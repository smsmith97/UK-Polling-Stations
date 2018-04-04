from data_collection.management.commands import BaseXpressDemocracyClubCsvImporter

class Command(BaseXpressDemocracyClubCsvImporter):
    council_id = 'E08000021'
    addresses_name = 'local.2018-05-03/Version 2/2nd Democracy_Club__03May2018 (1) Newcastle.tsv'
    stations_name = 'local.2018-05-03/Version 2/2nd Democracy_Club__03May2018 (1) Newcastle.tsv'
    elections = []
    csv_delimiter = '\t'

    def address_record_to_dict(self, record):

        if record.addressline6.strip() == 'NE16 6JE':
            return None

        if record.property_urn.strip() == '004510741266':
            return None

        return super().address_record_to_dict(record)
