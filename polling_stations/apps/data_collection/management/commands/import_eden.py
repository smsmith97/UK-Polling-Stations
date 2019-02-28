from data_collection.management.commands import BaseHalaroseCsvImporter


class Command(BaseHalaroseCsvImporter):
    council_id = "E07000030"
    addresses_name = "local.2019-05-02/Version 1/polling_station_export-2019-02-14.csv"
    stations_name = "local.2019-05-02/Version 1/polling_station_export-2019-02-14.csv"
    elections = ["local.2019-05-02"]

    def address_record_to_dict(self, record):
        rec = super().address_record_to_dict(record)
        uprn = record.uprn.strip().lstrip("0")

        if record.houseid == "9143":
            rec["postcode"] = "CA110TY"

        if uprn in [
            "100110693228",  # CA119HP -> CA119HR : Lark Hall Mews Robinson Street
            "10070538147",  # CA174DX -> CA174DS : Fox Tower View Brough, Kirkby Stephen
            "10000122517",  # CA102DQ -> CA102DG : Cross Fell Cottage Clifton Dykes
        ]:
            rec["accept_suggestion"] = True

        return rec
