# Postcode area -> (county, region) for England.
# Postcode areas cross county lines, so the county is the main one the area covers.
# Addresses that name a county override this (see build.py).
AREAS = {
    # South East
    "BN": ("East Sussex", "South East"), "RH": ("West Sussex", "South East"),
    "TN": ("Kent", "South East"), "ME": ("Kent", "South East"), "CT": ("Kent", "South East"),
    "DA": ("Kent", "South East"), "BR": ("Greater London", "London"),
    "GU": ("Surrey", "South East"), "KT": ("Surrey", "South East"),
    "SO": ("Hampshire", "South East"), "PO": ("Hampshire", "South East"),
    "RG": ("Berkshire", "South East"), "SL": ("Berkshire", "South East"),
    "OX": ("Oxfordshire", "South East"), "HP": ("Buckinghamshire", "South East"),
    "MK": ("Buckinghamshire", "South East"),
    # London
    "E": ("Greater London", "London"), "EC": ("Greater London", "London"), "N": ("Greater London", "London"),
    "NW": ("Greater London", "London"), "SE": ("Greater London", "London"), "SW": ("Greater London", "London"),
    "W": ("Greater London", "London"), "WC": ("Greater London", "London"), "CR": ("Greater London", "London"),
    "EN": ("Greater London", "London"), "HA": ("Greater London", "London"), "IG": ("Greater London", "London"),
    "RM": ("Greater London", "London"), "SM": ("Greater London", "London"), "TW": ("Greater London", "London"),
    "UB": ("Greater London", "London"), "WD": ("Hertfordshire", "East of England"),
    # East of England
    "AL": ("Hertfordshire", "East of England"), "SG": ("Hertfordshire", "East of England"),
    "LU": ("Bedfordshire", "East of England"), "CB": ("Cambridgeshire", "East of England"),
    "PE": ("Cambridgeshire", "East of England"), "CM": ("Essex", "East of England"),
    "CO": ("Essex", "East of England"), "SS": ("Essex", "East of England"),
    "IP": ("Suffolk", "East of England"), "NR": ("Norfolk", "East of England"),
    # South West
    "BA": ("Somerset", "South West"), "BS": ("Bristol", "South West"), "TA": ("Somerset", "South West"),
    "DT": ("Dorset", "South West"), "BH": ("Dorset", "South West"), "SP": ("Wiltshire", "South West"),
    "SN": ("Wiltshire", "South West"), "GL": ("Gloucestershire", "South West"),
    "EX": ("Devon", "South West"), "PL": ("Devon", "South West"), "TQ": ("Devon", "South West"),
    "TR": ("Cornwall", "South West"),
    # West Midlands
    "B": ("West Midlands", "West Midlands"), "CV": ("Warwickshire", "West Midlands"),
    "WV": ("West Midlands", "West Midlands"), "WS": ("Staffordshire", "West Midlands"),
    "DY": ("West Midlands", "West Midlands"), "ST": ("Staffordshire", "West Midlands"),
    "TF": ("Shropshire", "West Midlands"), "SY": ("Shropshire", "West Midlands"),
    "HR": ("Herefordshire", "West Midlands"), "WR": ("Worcestershire", "West Midlands"),
    # East Midlands
    "DE": ("Derbyshire", "East Midlands"), "NG": ("Nottinghamshire", "East Midlands"),
    "LE": ("Leicestershire", "East Midlands"), "NN": ("Northamptonshire", "East Midlands"),
    "LN": ("Lincolnshire", "East Midlands"), "S": ("South Yorkshire", "Yorkshire and the Humber"),
    # Yorkshire and the Humber
    "YO": ("North Yorkshire", "Yorkshire and the Humber"), "HG": ("North Yorkshire", "Yorkshire and the Humber"),
    "LS": ("West Yorkshire", "Yorkshire and the Humber"), "BD": ("West Yorkshire", "Yorkshire and the Humber"),
    "HX": ("West Yorkshire", "Yorkshire and the Humber"), "HD": ("West Yorkshire", "Yorkshire and the Humber"),
    "WF": ("West Yorkshire", "Yorkshire and the Humber"), "DN": ("South Yorkshire", "Yorkshire and the Humber"),
    "HU": ("East Riding of Yorkshire", "Yorkshire and the Humber"),
    # North West
    "M": ("Greater Manchester", "North West"), "OL": ("Greater Manchester", "North West"),
    "BL": ("Greater Manchester", "North West"), "WN": ("Greater Manchester", "North West"),
    "SK": ("Cheshire", "North West"), "WA": ("Cheshire", "North West"), "CW": ("Cheshire", "North West"),
    "CH": ("Cheshire", "North West"), "L": ("Merseyside", "North West"), "PR": ("Lancashire", "North West"),
    "BB": ("Lancashire", "North West"), "FY": ("Lancashire", "North West"), "LA": ("Cumbria", "North West"),
    "CA": ("Cumbria", "North West"),
    # North East
    "NE": ("Northumberland", "North East"), "DH": ("County Durham", "North East"),
    "DL": ("County Durham", "North East"), "SR": ("Tyne and Wear", "North East"),
    "TS": ("North Yorkshire", "North East"),
}

# County names that may appear in an address, mapped to (county, region).
COUNTY_WORDS = {
    "Cornwall": ("Cornwall", "South West"), "Devon": ("Devon", "South West"),
    "Somerset": ("Somerset", "South West"), "Dorset": ("Dorset", "South West"),
    "Wiltshire": ("Wiltshire", "South West"), "Gloucestershire": ("Gloucestershire", "South West"),
    "Hampshire": ("Hampshire", "South East"), "Isle Of Wight": ("Isle of Wight", "South East"),
    "Isle of Wight": ("Isle of Wight", "South East"), "Kent": ("Kent", "South East"),
    "East Sussex": ("East Sussex", "South East"), "West Sussex": ("West Sussex", "South East"),
    "Surrey": ("Surrey", "South East"), "Berkshire": ("Berkshire", "South East"),
    "Oxfordshire": ("Oxfordshire", "South East"), "Buckinghamshire": ("Buckinghamshire", "South East"),
    "Hertfordshire": ("Hertfordshire", "East of England"), "Bedfordshire": ("Bedfordshire", "East of England"),
    "Cambridgeshire": ("Cambridgeshire", "East of England"), "Essex": ("Essex", "East of England"),
    "Suffolk": ("Suffolk", "East of England"), "Norfolk": ("Norfolk", "East of England"),
    "Lincolnshire": ("Lincolnshire", "East Midlands"), "Northamptonshire": ("Northamptonshire", "East Midlands"),
    "Leicestershire": ("Leicestershire", "East Midlands"), "Rutland": ("Rutland", "East Midlands"),
    "Nottinghamshire": ("Nottinghamshire", "East Midlands"), "Derbyshire": ("Derbyshire", "East Midlands"),
    "Herefordshire": ("Herefordshire", "West Midlands"), "Worcestershire": ("Worcestershire", "West Midlands"),
    "Shropshire": ("Shropshire", "West Midlands"), "Staffordshire": ("Staffordshire", "West Midlands"),
    "Warwickshire": ("Warwickshire", "West Midlands"),
    "Cheshire": ("Cheshire", "North West"), "Lancashire": ("Lancashire", "North West"),
    "Cumbria": ("Cumbria", "North West"), "Northumberland": ("Northumberland", "North East"),
    "North Yorkshire": ("North Yorkshire", "Yorkshire and the Humber"),
    "West Yorkshire": ("West Yorkshire", "Yorkshire and the Humber"),
    "South Yorkshire": ("South Yorkshire", "Yorkshire and the Humber"),
    "East Riding Of Yorkshire": ("East Riding of Yorkshire", "Yorkshire and the Humber"),
    "Greater Manchester": ("Greater Manchester", "North West"),
    "London": ("Greater London", "London"),
}

# Town-level overrides where a postcode area straddles counties.
DISTRICT_OVERRIDES = {
    # Isle of Wight
    **{f"PO{n}": ("Isle of Wight", "South East") for n in range(30, 42)},
    # West Sussex parts of PO / RH / BN
    **{f"PO{n}": ("West Sussex", "South East") for n in (18, 19, 20, 21, 22)},
    **{f"BN{n}": ("West Sussex", "South East") for n in (5, 6, 11, 12, 13, 14, 15, 16, 17, 18, 43, 44, 99)},
    **{f"RH{n}": ("Surrey", "South East") for n in (1, 2, 3, 4, 5, 6, 7, 8, 9)},
    **{f"TN{n}": ("East Sussex", "South East") for n in (5, 6, 7, 19, 20, 21, 22, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40)},
    # Cornwall vs Devon in PL / EX
    **{f"PL{n}": ("Cornwall", "South West") for n in list(range(10, 18)) + list(range(22, 36))},
    "EX23": ("Cornwall", "South West"),
    # Peterborough area outside Cambridgeshire
    **{f"PE{n}": ("Lincolnshire", "East Midlands") for n in (6, 9, 10, 11, 12, 20, 21, 22, 23, 24, 25)},
    **{f"PE{n}": ("Norfolk", "East of England") for n in (13, 14, 30, 31, 32, 33, 34, 35, 36, 37, 38)},
    # Doncaster/Scunthorpe/Grimsby
    **{f"DN{n}": ("Lincolnshire", "East Midlands") for n in (21, 22, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41)},
    # Hereford/Gloucester border, Bristol area
    **{f"BS{n}": ("Somerset", "South West") for n in (21, 22, 23, 24, 25, 26, 27, 28, 29, 39, 40, 41, 48, 49)},
    **{f"BS{n}": ("Gloucestershire", "South West") for n in (30, 35, 36, 37)},
    # Bournemouth / Christchurch areas in Hampshire
    "BH24": ("Hampshire", "South East"), "BH25": ("Hampshire", "South East"),
    # SP: Hampshire parts
    **{f"SP{n}": ("Hampshire", "South East") for n in (6, 9, 10, 11)},
    # GU: Hampshire parts
    **{f"GU{n}": ("Hampshire", "South East") for n in (11, 12, 13, 14, 17, 30, 31, 32, 33, 34, 35, 46, 51, 52)},
    "GU28": ("West Sussex", "South East"), "GU29": ("West Sussex", "South East"),
    # SN: Oxfordshire parts
    **{f"SN{n}": ("Oxfordshire", "South East") for n in (7,)},
    # LA: Lancashire parts
    **{f"LA{n}": ("Lancashire", "North West") for n in (1, 2, 3, 4, 5, 6, 7)},
    # NE: Tyne and Wear parts
    **{f"NE{n}": ("Tyne and Wear", "North East") for n in range(1, 17)},
    # CW/SK Staffordshire and Derbyshire parts
    "ST13": ("Staffordshire", "West Midlands"), "SK17": ("Derbyshire", "East Midlands"),
    "SK13": ("Derbyshire", "East Midlands"), "SK23": ("Derbyshire", "East Midlands"),
    "S32": ("Derbyshire", "East Midlands"), "S33": ("Derbyshire", "East Midlands"),
    "S45": ("Derbyshire", "East Midlands"), "S41": ("Derbyshire", "East Midlands"), "S21": ("Derbyshire", "East Midlands"),
    # LE: Rutland
    "LE15": ("Rutland", "East Midlands"),
    # TS: County Durham parts
    "TS21": ("County Durham", "North East"),
    # CV: Warwickshire, OX: Oxfordshire edge
    "CV37": ("Warwickshire", "West Midlands"),
    # Wiltshire parts of BA
    **{f"BA{n}": ("Wiltshire", "South West") for n in (12, 13, 14, 15)},
    # Berwick-upon-Tweed is in England
    "TD15": ("Northumberland", "North East"),
}

# English postcode districts inside otherwise non-English areas.
ENGLISH_DISTRICTS = {"TD15", "CH1", "CH2", "CH3", "CH4", "CH64", "CH65", "CH66", "SY1", "SY2", "SY3", "SY4", "SY5",
                     "SY6", "SY7", "SY8", "SY9", "SY10", "SY11", "SY12", "SY13", "SY14"}

# Postcodes outside England (Scotland, Wales) to drop.
NON_ENGLAND_AREAS = {"TD", "DG", "EH", "KA", "ML", "G", "PA", "AB", "DD", "FK", "IV", "KW", "KY", "PH", "HS", "ZE",
                     "LL", "SA", "CF", "NP", "LD", "BT"}
