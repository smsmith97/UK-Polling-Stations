from data_importers.management.commands import BaseXpressDemocracyClubCsvImporter


class Command(BaseXpressDemocracyClubCsvImporter):
    council_id = "UTT"
    addresses_name = "2021-03-09T11:57:50.428803/Democracy_Club__06May2021_UDC.CSV"
    stations_name = "2021-03-09T11:57:50.428803/Democracy_Club__06May2021_UDC.CSV"
    elections = ["2021-05-06"]
    csv_delimiter = ","

    def address_record_to_dict(self, record):
        uprn = record.property_urn.strip().lstrip("0")

        if uprn in [
            "200004270735",  # "THE BARN, PLEDGDON GREEN, HENHAM, BISHOP'S STORTFORD"
            "10002182834",  # ANNEXE AT PLEDGDON LODGE BRICK END ROAD, HENHAM
            "200004261749",  # B LODGE, EASTON LODGE, LITTLE EASTON, DUNMOW
            "100091278781",  # GREENWOOD, CHURCH ROAD, CHRISHALL, ROYSTON
            "10090833371",  # NEW FARM ARKESDEN ROAD, WENDENS AMBO
            "100091276459",  # 6 CHICKNEY ROAD, HENHAM, BISHOP'S STORTFORD
            "100091277104",  # ARCHWAYS OLD MEAD ROAD, HENHAM
        ]:
            return None

        if record.addressline6 in ["CM22 6FG", "CM22 6TW"]:
            return None

        return super().address_record_to_dict(record)

    def station_record_to_dict(self, record):
        # St. Mary`s CoE Foundation Primary School, Stansted School Hall Hampton Road Stansted CM24 8FE
        if record.polling_place_id == "688":
            record = record._replace(polling_place_uprn="10090833547")

        # R A Butler School, R A Butler Academy - School Hall, South Road, Saffron Walden
        if record.polling_place_id == "547":
            record = record._replace(polling_place_uprn="200004267358")

        # Ashdon Village Hall Radwinter Road Ashdon Saffron Walden
        if record.polling_place_id == "676":
            record = record._replace(polling_place_psotcode="CB10 2HA'")

        return super().station_record_to_dict(record)
