import pymongo
from pymongo import MongoClient
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

pd.set_option('display.max_columns', None)
#Sample modified
# ==============================
# MongoDB Connection
# ==============================
myclient = MongoClient("mongodb://localhost:27017/")
mydb = myclient["repo"]
mydb2 = myclient["master_repo"]
mycol = mydb["golden_repo"]
mycol1 = mydb["guid_repo"]
mycol2 = mydb2["master_collection"]

# ==============================
# Get Input File Path
# ==============================
def get_input_filepath():
    doc = mycol2.find_one({}, {'IBUCKETPATH': 1})
    return doc['IBUCKETPATH'] if doc else None

# ==============================
# Get Output File Path
# ==============================
def get_output_filepath():
    doc = mycol2.find_one({}, {'WBUCKETPATH': 1})
    return doc['WBUCKETPATH'] if doc else None

# ==============================
# Compare GUIDs
# ==============================
def inputid(filepath):
    input_df = pd.read_csv(filepath)
    input_guids = input_df['guid'].astype(str).str.strip().tolist()

    cur = mycol1.find()
    golden_df = pd.DataFrame(list(cur))
    golden_guids = golden_df['GUID'].astype(str).str.strip().tolist()

    matched = []
    unmatched = []

    for guid in input_guids:
        if guid in golden_guids:
            print(f"✅ Matched: {guid}")
            matched.append(guid)
        else:
            print(f"❌ Unmatched: {guid}")
            unmatched.append(guid)

    return matched, unmatched

# ==============================
# Unmerge Operations
# ==============================
class Unmerge:
    def __init__(self, ids):
        self.ids = ids

    def unmerge_golden(self):
        for guid in self.ids:
            mycol.update_many({"GUID": guid}, {"$set": {"unmerge": "yes"}})
            print(f"🔹 Flagged {guid} for unmerge in golden_repo")

    def unmerge_remove_ind_guid(self):
        for guid in self.ids:
            mycol1.update_many({"GUID": guid}, {"$unset": {"Consolidation_Ind": ""}})
            print(f"🔹 Removed Consolidation_Ind for {guid}")

    def unmerge_guidrepo_update_oldguid(self):
        for guid in self.ids:
            mycol1.update_many({"GUID": guid}, {"$set": {"OLDGUID": guid}})
            print(f"🔹 Set OLDGUID = {guid}")

    def unmerge_empty_guid(self):
        for guid in self.ids:
            mycol1.update_many({"GUID": guid}, {"$set": {"GUID": ""}})
            print(f"🔹 Emptied GUID for {guid}")

# ==============================
# Delete OLDGUID Records
# ==============================
class RemoveUnmerge:
    def __init__(self, ids):
        self.ids = ids

    def delete_oldguids(self):
        for guid in self.ids:
            result = mycol1.delete_many({"OLDGUID": guid})
            print(f"🗑️ Deleted {result.deleted_count} record(s) for OLDGUID = {guid}")

# ==============================
# Write JSON Output
# ==============================
def write_json(filepath):
    cur = mycol1.find()
    df = pd.DataFrame(list(cur))
    df.to_json(filepath, default_handler=str, orient='records')
    print(f"📁 JSON written to {filepath}")

# ==============================
# Email Notifications
# ==============================
def send_email(matched, unmatched):
    sender_email = "jjrmohamed@gmail.com"
    sender_password = "eehp ubcu anvv ndif"
    receiver_email = "rjraman100@gmail.com"

    subject = "GUID matched results"
    body = ["GUID matching results\n"]
    body += [f"{guid} = matched" for guid in matched]
    body += [f"{guid} = unmatched" for guid in unmatched]

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText("\n".join(body), "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("📧 Email 1 sent successfully")
    except Exception as e:
        print("❌ Email 1 failed:", e)

def send_update_email(updated_guids):
    sender_email = "jjrmohamed@gmail.com"
    sender_password = "eehp ubcu anvv ndif"
    receiver_email = "rjraman100@gmail.com"

    subject = "GUID updated results"
    body = ["GUID results\n"]
    body += [f"{guid} - updated" for guid in updated_guids]

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText("\n".join(body), "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        print("📧 Email 2 sent successfully")
    except Exception as e:
        print("❌ Email 2 failed:", e)

# ==============================
# Main Pipeline
# ==============================
def main():
    input_path = get_input_filepath()
    output_path = get_output_filepath()

    if not input_path or not output_path:
        print("❌ Missing input or output path from MongoDB.")
        return

    matched, unmatched = inputid(input_path)

    if matched:
        unmerge = Unmerge(matched)
        unmerge.unmerge_golden()
        unmerge.unmerge_remove_ind_guid()
        unmerge.unmerge_guidrepo_update_oldguid()
        unmerge.unmerge_empty_guid()
        send_update_email(matched)

        remover = RemoveUnmerge(matched)
        remover.delete_oldguids()

    send_email(matched, unmatched)
    write_json(output_path)

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    main()
