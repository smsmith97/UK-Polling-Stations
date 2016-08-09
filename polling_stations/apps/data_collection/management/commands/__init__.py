"""
Defines the base importer classes to implement
"""
import abc
import csv
import json
import glob
import os
import re
import shapefile
import tempfile
import unicodedata
import urllib.request
import zipfile

from collections import namedtuple

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.gis import geos
from django.contrib.gis.gdal import DataSource, GDALException
from django.contrib.gis.geos import Point, GEOSGeometry
from django.db import connection
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe

from councils.models import Council
from data_collection.data_quality_report import (
    DataQualityReportBuilder,
    StationReport,
    DistrictReport,
    ResidentialAddressReport
)
from pollingstations.models import (
    PollingStation,
    PollingDistrict,
    ResidentialAddress
)
from data_collection.models import DataQuality
from addressbase.helpers import create_address_records_for_council


class CsvHelper:

    def __init__(self, filepath, encoding='utf-8', delimiter=','):
        self.filepath = filepath
        self.encoding = encoding
        self.delimiter = delimiter

    def parseCsv(self):
        file = open(self.filepath, 'rt', encoding=self.encoding)
        reader = csv.reader(file, delimiter=self.delimiter)
        header = next(reader)

        # mimic the data structure generated by ffs so existing import
        # scripts don't break
        replace = {
            ' ': '_',
            '-': '_',
            '.': '_',
            '(': '',
            ')': '',
        }
        clean = []
        for s in header:
            s = s.strip().lower()
            for k, v in replace.items():
                s = s.replace(k, v)
            while '__' in s:
                s = s.replace('__', '_')
            clean.append(s)
        RowKlass = namedtuple('RowKlass', clean)

        data = []
        for row in map(RowKlass._make, reader):
            data.append(row)

        file.close()
        return data


class Database:

    def teardown(self, council):
        PollingStation.objects.filter(council=council).delete()
        PollingDistrict.objects.filter(council=council).delete()
        ResidentialAddress.objects.filter(council=council).delete()

    def get_council(self, council_id):
        return Council.objects.get(pk=council_id)


class StationList:

    stations = []

    def __init__(self):
        self.stations = []

    def add(self, station):
        self.stations.append(station)

    def save(self):
        # make this more efficient
        for station in self.stations:
            PollingStation.objects.update_or_create(
                council=station['council'],
                internal_council_id=station['internal_council_id'],
                defaults=station,
            )

class DistrictList:

    districts = []

    def __init__(self):
        self.districts = []

    def add(self, district):
        self.districts.append(district)

    def save(self):
        # make this more efficient
        for district in self.districts:
            PollingDistrict.objects.update_or_create(
                council=district['council'],
                internal_council_id=district.get(
                    'internal_council_id', 'none'),
                defaults=district,
            )

class AddressList:

    addresses = []

    def __init__(self):
        self.addresses = []

    def add(self, address):
        self.addresses.append(address)

    def save(self):
        # make this more efficient
        for address in self.addresses:
            ResidentialAddress.objects.update_or_create(
                slug=address['slug'],
                defaults={
                    'council': address['council'],
                    'address': address['address'],
                    'postcode': address['postcode'],
                    'polling_station_id': address['polling_station_id'],
                }
            )

class BaseStationsImporter(metaclass=abc.ABCMeta):

    stations = StationList()

    @abc.abstractmethod
    def station_record_to_dict(self, record):
        pass

    @abc.abstractmethod
    def import_polling_stations(self):
        pass

    def add_polling_station(self, station_info):
        self.stations.add(station_info)


class BaseDistrictsImporter(metaclass=abc.ABCMeta):

    districts = DistrictList()

    def clean_poly(self, poly):
        if isinstance(poly, geos.Polygon):
            poly = geos.MultiPolygon(poly, srid=self.get_srid('districts'))
            return poly
        return poly

    @abc.abstractmethod
    def district_record_to_dict(self, record):
        pass

    @abc.abstractmethod
    def import_polling_districts(self, record):
        pass

    def add_polling_district(self, district_info):
        self.districts.add(district_info)


class BaseAddressesImporter(metaclass=abc.ABCMeta):

    addresses = AddressList()

    def slugify(self, value):
        """
        Custom slugify function:

        Convert to ASCII.
        Convert characters that aren't alphanumerics, underscores,
        or hyphens to hyphens
        Convert to lowercase.
        Strip leading and trailing whitespace.

        Unfortunately it is necessary to create wheel 2.0 in this situation
        because using django's standard slugify() function means that
        '1/2 Foo Street' and '12 Foo Street' both slugify to '12-foo-street'.
        This ensures that
        '1/2 Foo Street' becomes '1-2-foo-street' and
        '12 Foo Street' becomes '12-foo-street'

        This means we can avoid appending an arbitrary number and minimise
        disruption to the public URL schema if a council provides updated data
        """
        value = force_text(value)
        value = unicodedata.normalize(
            'NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub('[^\w\s-]', '-', value).strip().lower()
        return mark_safe(re.sub('[-\s]+', '-', value))

    def get_slug(self, address_info):
        # if we have a uprn, use that as the slug
        if 'uprn' in address_info:
            if address_info['uprn']:
                return address_info['uprn']

        # otherwise build a slug from the other data we have
        return self.slugify(
            "%s-%s-%s-%s" % (
                self.council.pk,
                address_info['polling_station_id'],
                address_info['address'],
                address_info['postcode']
            )
        )

    @abc.abstractmethod
    def address_record_to_dict(self, record):
        pass

    @abc.abstractmethod
    def import_residential_addresses(self):
        pass

    def add_residential_address(self, address_info):

        """
        strip all whitespace from postcode and convert to uppercase
        this will make it easier to query this based on user-supplied postcode
        """
        address_info['postcode'] =\
            re.sub('[^A-Z0-9]', '', address_info['postcode'].upper())

        # generate a unique slug so we can provide a consistent url
        slug = self.get_slug(address_info)
        address_info['slug'] = slug

        self.addresses.add(address_info)


class PostProcessingMixin:

    def clean_postcodes_overlapping_districts(self):
        data = create_address_records_for_council(self.council)
        self.postcodes_contained_by_district = data['no_attention_needed']
        self.postcodes_with_addresses_generated = data['addresses_created']

    @transaction.atomic
    def clean_ambiguous_addresses(self):
        table_name = ResidentialAddress()._meta.db_table
        cursor = connection.cursor()
        cursor.execute("""
        DELETE FROM {0} WHERE CONCAT(address, postcode) IN (
         SELECT concat_address FROM (
             SELECT CONCAT(address, postcode) AS concat_address, COUNT(*) AS c
             FROM {0}
             WHERE council_id=%s
             GROUP BY CONCAT(address, postcode)
            ) as dupes
            WHERE dupes.c > 1
        )
        """.format(table_name), [self.council_id])


class BaseImporter(BaseCommand, PostProcessingMixin, metaclass=abc.ABCMeta):
    srid = 27700
    districts_srid = None
    council_id = None
    base_folder_path = None
    stations_name = "polling_places"
    districts_name = "polling_districts"
    csv_encoding = 'utf-8'
    csv_delimiter = ','
    db = Database()

    def get_srid(self, type=None):
        if type == 'districts' and self.districts_srid is not None:
            return self.districts_srid
        else:
            return self.srid

    @abc.abstractmethod
    def import_data(self):
        pass

    def post_import(self):
        raise NotImplementedError

    def report(self):
        # build report
        report = DataQualityReportBuilder(self.council_id)
        station_report = StationReport(self.council_id)
        district_report = DistrictReport(self.council_id)
        address_report = ResidentialAddressReport(self.council_id)
        report.build_report()

        # save a static copy in the DB that we can serve up on the website
        record = DataQuality.objects.get_or_create(
            council_id=self.council_id,
        )
        record[0].report = report.generate_string_report()
        record[0].num_stations = station_report.get_stations_imported()
        record[0].num_districts = district_report.get_districts_imported()
        record[0].num_addresses = address_report.get_addresses_imported()
        record[0].save()

        # output to console
        report.output_console_report()

    @property
    def data_path(self):
        data_private = getattr(self, 'private', False)
        if data_private:
            path = getattr(
                settings,
                'PRIVATE_DATA_PATH',
                '../polling_station_data/')
        else:
            path = "./"
        return os.path.abspath(path)

    def handle(self, *args, **kwargs):
        if self.council_id is None:
            self.council_id = args[0]

        self.council = self.db.get_council(self.council_id)

        # Delete old data for this council
        self.db.teardown(self.council)

        if getattr(self, 'local_files', True):
            if self.base_folder_path is None:
                path = os.path.join(
                    self.data_path,
                    'data/{0}-*'.format(self.council_id))
                self.base_folder_path = glob.glob(path)[0]

        self.import_data()

        # Optional step for post import tasks
        try:
            self.post_import()
        except NotImplementedError:
            pass

        self.clean_ambiguous_addresses()

        # For areas with shape data, use AddressBase
        # to clean up overlapping postcode
        self.clean_postcodes_overlapping_districts()

        # save and output data quality report
        self.report()


class BaseStationsDistrictsImporter(
    BaseImporter, BaseStationsImporter, BaseDistrictsImporter):

    def import_data(self):
        self.stations = StationList()
        self.districts = DistrictList()
        self.import_polling_districts()
        self.import_polling_stations()
        self.districts.save()
        self.stations.save()


class BaseStationsAddressesImporter(
    BaseImporter, BaseStationsImporter, BaseAddressesImporter):

    def import_data(self):
        self.stations = StationList()
        self.addresses = AddressList()
        self.import_residential_addresses()
        self.import_polling_stations()
        self.addresses.save()
        self.stations.save()


class BaseCsvStationsImporter(BaseStationsImporter):

    def get_stations(self):
        stations_file = os.path.join(self.base_folder_path, self.stations_name)
        helper = CsvHelper(stations_file, self.csv_encoding, self.csv_delimiter)
        data = helper.parseCsv()
        return data

    def import_polling_stations(self):
        stations = self.get_stations()
        seen = set()
        for station in stations:
            if hasattr(self, 'get_station_hash'):
                station_hash = self.get_station_hash(station)
                if station_hash in seen:
                    continue
                else:
                    station_info = self.station_record_to_dict(station)
                    seen.add(station_hash)
            else:
                station_info = self.station_record_to_dict(station)

            if station_info is None:
                continue
            if 'council' not in station_info:
                station_info['council'] = self.council
            self.add_polling_station(station_info)


class BaseShpStationsImporter(BaseStationsImporter):

    def get_stations(self):
        sf = shapefile.Reader("{0}/{1}".format(
            self.base_folder_path,
            self.stations_name)
        )
        return sf.shapeRecords()

    def import_polling_stations(self):
        stations = self.get_stations()
        for station in stations:
            station_info = self.station_record_to_dict(station.record)

            if station_info is None:
                continue
            if 'council' not in station_info:
                station_info['council'] = self.council

            station_info['location'] = Point(
                *station.shape.points[0],
                srid=self.get_srid())
            self.add_polling_station(station_info)


class BaseKmlStationsImporter(BaseStationsImporter):

    def get_stations(self, kml):
        ds = DataSource(kml)
        return ds[0]

    def add_kml_stations(self, kml):
        stations = self.get_stations(kml)
        for station in stations:
            station_info = self.station_record_to_dict(station)

            if station_info is None:
                continue
            if 'council' not in station_info:
                station_info['council'] = self.council

            self.add_polling_station(station_info)

    def import_polling_stations(self):
        # if we ever need it, implement this
        raise NotImplementedError


class BaseShpDistrictsImporter(BaseDistrictsImporter):

    def get_districts(self):
        sf = shapefile.Reader("{0}/{1}".format(
            self.base_folder_path,
            self.districts_name)
        )
        return sf.shapeRecords()

    def import_polling_districts(self):
        districts = self.get_districts()
        for district in districts:
            district_info = self.district_record_to_dict(district.record)

            if district_info is None:
                continue
            if 'council' not in district_info:
                district_info['council'] = self.council

            geojson = json.dumps(district.shape.__geo_interface__)
            poly = self.clean_poly(
                GEOSGeometry(geojson, srid=self.get_srid('districts')))
            district_info['area'] = poly
            self.add_polling_district(district_info)


class BaseJsonDistrictsImporter(BaseDistrictsImporter):

    def get_districts(self):
        districtsfile = os.path.join(
            self.base_folder_path, self.districts_name)
        districts = json.load(open(districtsfile))
        return districts['features']

    def import_polling_districts(self):
        districts = self.get_districts()

        for district in districts:
            district_info = self.district_record_to_dict(district)

            if district_info is None:
                continue
            if 'council' not in district_info:
                district_info['council'] = self.council

            poly = self.clean_poly(
                GEOSGeometry(json.dumps(district['geometry']),
                                srid=self.get_srid('districts')))
            district_info['area'] = poly
            self.add_polling_district(district_info)


class BaseKmlDistrictsImporter(BaseDistrictsImporter):

    def strip_z_values(self, geojson):
        districts = json.loads(geojson)
        districts['type'] = 'Polygon'
        for points in districts['coordinates'][0][0]:
            if len(points) == 3:
                points.pop()
        districts['coordinates'] = districts['coordinates'][0]
        return json.dumps(districts)

    def get_districts(self, kml):
        try:
            ds = DataSource(kml)
        except GDALException:
            # This is very strainge – sometimes the above will fail the first
            # time, but not the second. Seen on OS X with GDAL 2.2.0
            ds = DataSource(kml)
        return ds[0]

    def add_kml_districts(self, kml):
        districts = self.get_districts(kml)
        for district in districts:
            district_info = self.district_record_to_dict(district)

            if district_info is None:
                continue
            if 'council' not in district_info:
                district_info['council'] = self.council

            self.add_polling_district(district_info)

    def import_polling_districts(self):
        districtsfile = os.path.join(
            self.base_folder_path, self.districts_name)

        if not districtsfile.endswith('.kmz'):
            self.add_kml_districts(districtsfile)
            return

        # It's a .kmz file !
        # Because the C lib that the django DataSource is wrapping
        # expects a file on disk, let's extract the actual KML to a tmpfile.
        kmz = zipfile.ZipFile(districtsfile, 'r')
        kmlfile = kmz.open('doc.kml', 'r')

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(kmlfile.read())
            self.add_kml_districts(tmp.name)
            tmp.close()


class BaseCsvAddressesImporter(BaseAddressesImporter):

    def get_addresses(self):
        addresses_file = os.path.join(self.base_folder_path, self.addresses_name)
        helper = CsvHelper(addresses_file, self.csv_encoding, self.csv_delimiter)
        data = helper.parseCsv()
        return data

    def import_residential_addresses(self):
        addresses = self.get_addresses()
        for address in addresses:
            address_info = self.address_record_to_dict(address)
            if address_info is None:
                continue
            if 'council' not in address_info:
                address_info['council'] = self.council
            self.add_residential_address(address_info)


"""
Stations in CSV format
Districts in SHP format
"""
class BaseCsvStationsShpDistrictsImporter(
    BaseStationsDistrictsImporter,
    BaseCsvStationsImporter,
    BaseShpDistrictsImporter):

    pass


"""
Stations in SHP format
Districts in SHP format
"""
class BaseShpStationsShpDistrictsImporter(
    BaseStationsDistrictsImporter,
    BaseShpStationsImporter,
    BaseShpDistrictsImporter):

    pass


"""
Stations in CSV format
Districts in JSON format
"""
class BaseCsvStationsJsonDistrictsImporter(
    BaseStationsDistrictsImporter,
    BaseCsvStationsImporter,
    BaseJsonDistrictsImporter):

    pass


"""
Stations in CSV format
Districts in KML format
"""
class BaseCsvStationsKmlDistrictsImporter(
    BaseStationsDistrictsImporter,
    BaseCsvStationsImporter,
    BaseKmlDistrictsImporter):

    districts_srid = 4326

    # this is mainly here for legacy compatibility
    def district_record_to_dict(self, record):
        geojson = self.strip_z_values(record.geom.geojson)
        poly = self.clean_poly(
            GEOSGeometry(geojson, srid=self.get_srid('districts')))
        return {
            'internal_council_id': record['Name'].value,
            'name': record['Name'].value,
            'area': poly
        }


"""
Stations in CSV format
Addresses in CSV format
"""
class BaseCsvStationsCsvAddressesImporter(
    BaseStationsAddressesImporter,
    BaseCsvStationsImporter,
    BaseCsvAddressesImporter):

    pass


"""
Stations in SHP format
Addresses in CSV format
"""
class BaseShpStationsCsvAddressesImporter(
    BaseStationsAddressesImporter,
    BaseShpStationsImporter,
    BaseCsvAddressesImporter):

    pass


class BaseGenericApiImporter(BaseStationsDistrictsImporter):
    srid = 4326
    districts_srid = 4326
    districts_url = None
    stations_url = None
    local_files = False

    def import_data(self):
        # deal with 'stations only' or 'districts only' data
        self.districts = DistrictList()
        self.stations = StationList()
        if self.districts_url is not None:
            self.import_polling_districts()
        if self.stations_url is not None:
            self.import_polling_stations()
        self.districts.save()
        self.stations.save()

    def import_polling_districts(self):
        with tempfile.NamedTemporaryFile() as tmp:
            req = urllib.request.urlretrieve(self.districts_url, tmp.name)
            self.add_districts(tmp.name)
        return

    def import_polling_stations(self):
        with tempfile.NamedTemporaryFile() as tmp:
            req = urllib.request.urlretrieve(self.stations_url, tmp.name)
            self.add_stations(tmp.name)
        return

    def add_districts(self, filename):
        raise NotImplementedError

    def add_stations(self, filename):
        raise NotImplementedError


"""
Stations in KML format
Districts in KML format
"""
class BaseApiKmlStationsKmlDistrictsImporter(
    BaseGenericApiImporter,
    BaseKmlStationsImporter,
    BaseKmlDistrictsImporter):

    def add_districts(self, filename):
        self.add_kml_districts(filename)

    def add_stations(self, filename):
        self.add_kml_stations(filename)
