from data_importers.management.commands import BaseDemocracyCountsCsvImporter


class Command(BaseDemocracyCountsCsvImporter):
    council_id = "E08000016"
    addresses_name = "parl.2019-12-12/Version 1/Democracy Club PD.csv"
    stations_name = "parl.2019-12-12/Version 1/Democracy Club PS.csv"
    elections = ["parl.2019-12-12"]
    allow_station_point_from_postcode = False

    def station_record_to_dict(self, record):

        # DARFIELD COMMUNITY CENTRE, DARHAVEN, DARFIELD, BARNSLEY
        if record.stationcode == "59":
            record = record._replace(xordinate="441313", yordinate="404680")

        # TEMPORARY BUILDING AT GRASMERE CRESCENT
        if record.stationcode == "10":
            record = record._replace(xordinate="", yordinate="")

        return super().station_record_to_dict(record)

    def address_record_to_dict(self, record):
        rec = super().address_record_to_dict(record)
        uprn = record.uprn.strip().lstrip("0")

        if record.uprn == "100050685041":
            rec["postcode"] = "S35 7AL"

        if record.postcode in [
            "S70 5UD",
            "S36 9DB",
            "S75 6JX",
        ]:
            return None

        if uprn in [
            "100050657644",  # S754LB -> S754DX : Adam Laithe Barn, Silkstone Lane, Silkstone, Barnsley
            "100050629116",  # S749AB -> S639LR : 14a High Street, Hoyland, Barnsley
            "10032781549",  # S712EP -> S712EW : Manor Farm, 58 Cross Street, Monk Bretton, Barnsley
            "100050638067",  # S715PA -> S715PE : Sunnybank Farm, Lund Lane, Lundwood, Barnsley
            "2007006814",  # S713HG -> S713HL : Caravan Shaw Lane, Shaw Lane, Carlton, Barnsley
            "100050684397",  # S357AT -> S357AW : Rock Cottage, Crane Moor Road, Crane Moor, Sheffield
            "10022884646",  # S357DY -> S357AT : Rockside, The Old Rock Inn, Crane Moor Road, Crane Moor, Sheffield
            "10032791344",  # S706TU -> S706TY : The Barn, Rob Royd Farm, Hound Hill Lane, Worsbrough, Barnsley
        ]:
            rec["accept_suggestion"] = False

        return rec
