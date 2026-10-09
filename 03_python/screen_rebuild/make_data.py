"""Generates the practice data. Run once: python make_data.py [--big N]"""
import csv, random, sqlite3, sys, pathlib
random.seed(7)
root = pathlib.Path(__file__).parent
codes = [f"P{n:03d}" for n in range(1, 41)]
names = ["Ibuprofen 200mg","Saline 0.9% 500mL","Nitrile Gloves M","Gauze Pad 4x4","Insulin Pen Needle","Alcohol Prep Pad",
 "Syringe 10mL","IV Catheter 20G","Blood Pressure Cuff","Pulse Oximeter","Thermometer Probe Cover","Surgical Mask","N95 Respirator",
 "Bandage Roll 3in","Tongue Depressor","Specimen Cup","Lancet 28G","Test Strip Pack","Hand Sanitizer 8oz","Exam Table Paper",
 "Cotton Swab","Medical Tape 1in","Ice Pack","Heating Pad","Wrist Brace","Knee Brace","Crutch Tips","Cane Quad","Pill Organizer",
 "Nebulizer Kit","Spacer Chamber","Peak Flow Meter","Glucose Gel","Hydrocortisone Cream","Antibiotic Ointment","Eye Wash 4oz",
 "Ear Syringe","Splint Finger","Cold Compress","Sterile Water 1L"]

def products_sql():
    rows = [f"({i},'{c}','{n}',1)" for i,(c,n) in enumerate(zip(codes,names),1)]
    rows.append("(41,'P017','Lancet 30G (discontinued)',0)")  # same code twice: one inactive
    return ("DROP TABLE IF EXISTS products;\nCREATE TABLE products (product_id INTEGER PRIMARY KEY, product_code TEXT NOT NULL, "
            "product_name TEXT NOT NULL, is_active INTEGER NOT NULL);\nINSERT INTO products VALUES\n" + ",\n".join(rows) + ";\n")

def clean_row(i):
    return [f"T{i:06d}", f"2026-{random.randint(1,9):02d}-{random.randint(1,28):02d}", random.choice(codes),
            str(random.randint(1,12)), f"{random.uniform(1,90):.2f}", f"S{random.randint(1,8):02d}", ""]

def write_small():
    rows = [clean_row(i) for i in range(1, 201)]
    rows[10][6] = "gift, wrapped"; rows[42][6] = 'customer said "rush"'
    rows[20][2] = "P999"; rows[71][2] = "P404"; rows[130][2] = "Q001"
    rows[33][2] = " p012 "; rows[88][2] = "P007 "
    rows[55][2] = ""; rows[99][3] = ""
    rows[64][3] = "two"; rows[150][1] = "2026-13-40"
    rows[120][2] = "P017"
    rows += [rows[5][:], rows[6][:], rows[7][:]]                    # exact duplicates
    conflict = rows[15][:]; conflict[3] = "99"; rows.append(conflict)  # same id, different values
    random.shuffle(rows)
    with open(root/"data/transactions.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["transaction_id","transaction_date","product_code","quantity","unit_price","store_id","notes"])
        w.writerows(rows)
    with open(root/"data/transactions.csv","a") as f:
        f.write("T009001,2026-05-05,P003,4,12.50,S02,,EXTRA_FIELD\n")   # wrong column count
        f.write("T009002,2026-05-06,P004\n")                            # truncated line

def write_big(n):
    with open(root/"data/transactions_big.csv","w",newline="") as f:
        w = csv.writer(f); w.writerow(["transaction_id","transaction_date","product_code","quantity","unit_price","store_id","notes"])
        for i in range(1, n+1): w.writerow(clean_row(i))

(root/"data/products.sql").write_text(products_sql())
con = sqlite3.connect(root/"data/products.db"); con.executescript(products_sql()); con.close()
write_small()
if "--big" in sys.argv: write_big(int(sys.argv[sys.argv.index("--big")+1]))
print("data ready")
