import os
import datetime
from tkinter import messagebox


def build_record_block(data):
    """
    Create a formatted record block from a dictionary.
    Adds optional funding fields when present, and keeps the legacy
    trailing separator so existing write/join logic stays unchanged.
    """
    current_time = datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")

    # Core fields (same order as before)
    lines = [
        f"number||{data.get('number', '')}",
        f"authors||{data.get('authors', '')}",
        f"title||{data.get('title', '')}",
        f"bookjour||{data.get('bookjour', '')}",
        f"location||{data.get('location', '')}",
        f"volume||{data.get('volume', '')}",
        f"pages||{data.get('pages', '')}",
        f"year||{data.get('year', '')}",
        f"vitatyp||{data.get('vitatyp', '')}",
    ]

    # --- Optional Funding Proposals fields (write only when non-empty) ---
    fy = str(data.get('funding_year', '')).strip()
    tot = str(data.get('total_amount', data.get('amount', ''))).strip()  # legacy fallback
    use = str(data.get('usable_amount', '')).strip()
    dec = str(data.get('decision', '')).strip()

    if fy:
        lines.append(f"funding_year||{fy}")
    if tot:
        lines.append(f"total_amount||{tot}")  # new standardized key
    if use:
        lines.append(f"usable_amount||{use}")  # new key
    if dec:
        lines.append(f"decision||{dec}")

    # Rest fields (unchanged)
    lines.extend([
        f"subject1||{data.get('subject1', '')}",
        f"subject2||{data.get('subject2', '')}",
        f"duplicateoknumber||{data.get('duplicateoknumber', '')}",
        f"pdfpresent||{data.get('pdfpresent', '')}",
        f"pdfpath||{data.get('pdfpath', '')}",
        # Preserve existing dateentered if present; otherwise use current time
        f"dateentered||{data.get('dateentered', current_time)}",
        "*********$$$$$$$$$$$$",
    ])

    # IMPORTANT: keep the trailing newline to match your legacy format
    return "\n".join(lines) + "\n"


def split_header_and_records(file_path):
    """
    Split a .cnt file into header (before first record) and records (after first number||).
    """
    header = []
    records = []

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        found_first_record = False
        current_record = []

        for line in lines:
            if not found_first_record and line.strip().lower().startswith("number||"):
                found_first_record = True

            if not found_first_record:
                header.append(line)
            else:
                current_record.append(line)

        full_text = "".join(current_record)
        records = full_text.split("*********$$$$$$$$$$$$")
        records = [r.strip() for r in records if r.strip()]

    return header, records


def save_to_cnt(file_path, data):
    """
    Append ONE new record to the .cnt file (preserve existing header and records).
    This function does NOT rewrite header or other records; it truly appends.
    """
    try:
        if not data.get("authors", "").strip() and not data.get("title", "").strip():
            messagebox.showwarning("Invalid Data", "Authors and Title cannot both be empty.")
            return

        block = build_record_block(data)  # includes the trailing separator per your legacy format
        with open(file_path, "a", encoding="utf-8") as f:  # <-- append mode
            f.write(block)

        print(f"[INFO] Appended 1 record to {file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while saving data: {str(e)}")



def overwrite_record_in_cnt(file_path, data, show_message=True):
    """
    Overwrite a specific record (by number) in the .cnt file.
    Record blocks produced by build_record_block() include a trailing separator,
    so we strip that off here and re-insert separators uniformly when joining.
    """
    try:
        target_number = str(data.get("number", "")).strip()
        if not target_number:
            if show_message:
                messagebox.showerror("Error", "No valid number provided for overwrite.")
            return

        header, records = split_header_and_records(file_path)

        # Build the new block and strip OFF the trailing separator because we add it later uniformly
        new_record = build_record_block(data).strip()
        if new_record.endswith("*********$$$$$$$$$$$$"):
            # remove the last line (the separator) from the new block
            new_record = "\n".join(new_record.splitlines()[:-1]).strip()

        replaced = False
        updated_records = []

        for record in records:
            # Each 'record' here is a block WITHOUT its separator (split removed it)
            lines = [line.strip() for line in record.splitlines() if line.strip()]

            if any(line.lower() == f"number||{target_number}".lower() for line in lines):
                # append the block WITHOUT its own separator
                updated_records.append(new_record)
                replaced = True
            else:
                # keep original block (no separator)
                updated_records.append("\n".join(lines))

        if not replaced:
            if show_message:
                messagebox.showwarning("Warning", f"Record number {target_number} not found.")
            return

        # Uniformly join with one separator between records and one at the end
        sep = "\n*********$$$$$$$$$$$$\n"
        final_content = "".join(header) + sep.join(updated_records) + sep

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"[INFO] Record {target_number} updated.")
        if show_message:
            messagebox.showinfo("Success", f"Record {target_number} updated.")

    except Exception as e:
        if show_message:
            messagebox.showerror("Error", f"Failed to overwrite record: {str(e)}")



def overwrite_all_records_in_cnt(file_path, data_list):
    """
    Overwrite the entire .cnt file with a list of new records, preserving the original header.
    """
    try:
        header, _ = split_header_and_records(file_path)
        all_blocks = [build_record_block(record).strip() for record in data_list]
        final_content = "".join(header) + "\n".join(all_blocks)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        print(f"[INFO] All records overwritten in {file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to overwrite all records: {str(e)}")

def append_records_to_cnt(file_path, data_list):
    """
    Append a list of new records to the end of a .cnt file (preserve original content).
    """
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            for record in data_list:
                block = build_record_block(record)
                f.write(block)
        print(f"[INFO] {len(data_list)} new records appended to {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to append records: {str(e)}")


