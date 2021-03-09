from data_importers.management.commands import BaseXpressDemocracyClubCsvImporter


class Command(BaseXpressDemocracyClubCsvImporter):
    council_id = "NWP"
    addresses_name = "2021-03-08T19:45:53.092814/Newport Democracy_Club__06May2021.tsv"
    stations_name = "2021-03-08T19:45:53.092814/Newport Democracy_Club__06May2021.tsv"
    elections = ["2021-05-06"]
    csv_delimiter = "\t"
    csv_encoding = "latin-1"

    def address_record_to_dict(self, record):
        uprn = record.property_urn.strip().lstrip("0")

        if uprn in [
            "10002155274",  # WERN FARM, RHIWDERIN, NEWPORT
            "10002155651",  # 196 CARDIFF ROAD, NEWPORT
            "10002147773",  # 188 CARDIFF ROAD, NEWPORT
            "100100654811",  # MEADOW BROOK, PENHOW, CALDICOT
            "100100654809",  # GREENACRES, PENHOW, CALDICOT
            "100100654807",  # FLAT 2 25 CARDIFF ROAD, NEWPORT
            "100100654805",  # FLAT 5 25 CARDIFF ROAD, NEWPORT
            "100100654804",  # 512 MONNOW WAY, BETTWS, NEWPORT
            "10090277427",  # 190 CARDIFF ROAD, NEWPORT
            "10090277428",  # 194 CARDIFF ROAD, NEWPORT
            "10090277426",  # 192 CARDIFF ROAD, NEWPORT
            "100100677933",  # TY TERNION, LODGE ROAD, CAERLEON, NEWPORT
            "10093295441",  # 39 REMBRANDT WAY, NEWPORT
            "10090277366",  # ORCHARD FARM, ST. BRIDES WENTLOOGE, NEWPORT
            "10010553788",  # BLUEBELL COTTAGE, ST. BRIDES WENTLOOGE, NEWPORT
            "10002154176",  # 8 MAPLE CLOSE, NEWPORT
            "100101046500",  # FLAT 3 25 CARDIFF ROAD, NEWPORT
            "10090275166",  # 5C TURNER STREET, NEWPORT
            "10002153590",  # 124B CHEPSTOW ROAD, NEWPORT
            "100100668792",  # 124A CHEPSTOW ROAD, NEWPORT
            "10002153797",  # YEW TREE COTTAGE, HENDREW LANE, LLANDEVAUD, NEWPORT
            "200001705281",  # THE LAURELS, GREENACRES, PENHOW, CALDICOT
            "10009646166",  # RED ROBIN HOUSE, LLANDEVAUD, NEWPORT
            "200001652454",  # LITTLE CAERLICKEN, CAERLICYN LANE, LANGSTONE, NEWPORT
            "200002951720",  # ABBEYFIELD SOCIETY, ELEANOR HODSON HOUSE, PILLMAWR ROAD, CAERLEON, NEWPORT
            "10014125673",  # MANAGERS ACCOMMODATION THE WINDSOR CLUB 154-156 CONWAY ROAD, NEWPORT
        ]:
            return None

        if record.post_code in ["NP19 9BX", "NP10 8AT"]:
            return None

        return super().address_record_to_dict(record)

    def station_record_to_dict(self, record):
        if (
            record.polling_place_id == "12117"
        ):  # Michaelstone-Y-Fedw Village Hall Michaelstone Cardiff CF3 6XT
            record = record._replace(polling_place_postcode="CF3 6XS")

        if (
            record.polling_place_id == "12084"
        ):  # Graig Community Hall Caerphilly Road Bassaleg Newport NP10 9LE
            record = record._replace(polling_place_postcode="NP10 8HZ")

        if (
            record.polling_place_id == "12147"
        ):  # Mount Pleasant Primary School Ruskin Avenue Rogerstone Newport
            record = record._replace(polling_place_postcode="NP10 0AA")

        if (
            record.polling_place_id == "12022"
        ):  # Nursery Unit Glasllwch Primary School Melbourne Way Newport NP20 3RN
            record = record._replace(polling_place_postcode="NP20 3RH")

        if (
            record.polling_place_id == "12162"
        ):  # All Saints Community Church Brynglas Road Newport NP20 5QU
            record = record._replace(polling_place_postcode="NP20 5RY")

        if (
            record.polling_place_id == "12042"
        ):  # Monnow Primary School Darent Close Newport NP20 6SQ
            record = record._replace(polling_place_postcode="NP20 7SQ")

        if (
            record.polling_place_id == "11973"
        ):  # Maindee Unlimited (Old Library) 79 Chepstow Road Newport NP18 8BY
            record = record._replace(polling_place_postcode="NP19 8BY")

        if record.polling_place_id == "11949":  # East Hub 282 Ringland Circle Newport
            record = record._replace(polling_place_postcode="NP19 9PS")

        return super().station_record_to_dict(record)
