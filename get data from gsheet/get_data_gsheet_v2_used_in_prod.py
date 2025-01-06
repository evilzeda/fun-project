import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import date, timedelta
import pandas as pd
import numpy as np
import csv

def auth_to_google_v2(json_auth_file: str, spreadsheet_id: str, worksheet_gid: str):
    """
    Authenticate to google sheet and select worksheet by GID
    
    Args:
        json_auth_file (str): path of json credential auth
        spreadsheet_id (str): id of spreadsheet
        worksheet_gid (str): gid of worksheet
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = Credentials.from_service_account_file(
        filename=json_auth_file, scopes=SCOPES)
    gc = gspread.authorize(credentials=credentials)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    
    # Get all worksheets and find the one with matching gid
    worksheets = spreadsheet.worksheets()
    worksheet = None
    for sheet in worksheets:
        if str(sheet.id) == worksheet_gid:
            worksheet = sheet
            break
            
    if worksheet is None:
        raise ValueError(f"No worksheet found with gid: {worksheet_gid}")
        
    return worksheet

def make_headers_unique(headers):
    """
    Make header names unique by appending numbers to duplicates.
    
    Args:
        headers (list): List of header names
    
    Returns:
        list: List of unique header names
    """
    seen = {}
    unique_headers = []
    
    for header in headers:
        if header in seen:
            seen[header] += 1
            unique_headers.append(f"{header}_{seen[header]}")
        else:
            seen[header] = 0
            unique_headers.append(header)
    
    return unique_headers

def is_valid_pos_code(pos_code):
    """
    Check if the POS code is valid (not empty, not '-', and not null)
    
    Args:
        pos_code: The POS code to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if pd.isna(pos_code) or str(pos_code).strip() == '' or str(pos_code).strip() == '-':
        return False
    return True

def clean_and_split_coordinates(coord_str):
    """
    Clean and split coordinates into latitude and longitude.
    Handles various formats including spaces, periods, and commas as separators.
    Returns "0.0" for null/blank values.
    
    Args:
        coord_str: String containing coordinates
        
    Returns:
        tuple: (latitude, longitude) as strings, with "0.0" for invalid/null values
    """
    if pd.isna(coord_str) or coord_str == '' or str(coord_str).strip() == '0':
        return "0.0", "0.0"

    # Convert to string and clean basic whitespace
    coord_str = str(coord_str).strip()
    
    # First try to split by comma
    parts = coord_str.split(',')
    
    # If we don't have exactly 2 parts after comma split, try period split
    if len(parts) != 2:
        # Look for a period followed by a space, which likely separates lat/lon
        parts = coord_str.split('. ')
        if len(parts) != 2:
            # If still not split correctly, try to split by space
            parts = coord_str.split()
            if len(parts) != 2:
                return "0.0", "0.0"  # Return default values if we can't split properly

    try:
        # Clean up each part
        lat = parts[0].strip()
        lon = parts[1].strip()
        
        # Convert to float and back to string to validate and standardize format
        lat = str(float(lat))
        lon = str(float(lon))
        
        # Basic validation of coordinate ranges
        if not (-90 <= float(lat) <= 90) or not (-180 <= float(lon) <= 180):
            return "0.0", "0.0"
            
        return lat, lon
        
    except ValueError:
        return "0.0", "0.0"

def get_data_sheet_one():
    """
    Inserts data from a CSV file into a Google Spreadsheet.
    Handles duplicate headers by making them unique.
    Uses worksheet GID instead of index.
    """
    spreadsheet_id = "1YniWV0eQVH5cMRrrFLjevFnqaRz1bDagJHQYcM_pDF0"
    worksheet_gids = ["1019753355"]

    columns_to_keep = [
        'POSCode',
        'POS Name',
        'Foto Lokasi Bagian Dalam',
        'Foto Lokasi Bagian Depan',
        'Lokasi',
        'Kota/Kabupaten',
        'Jenis Bangunan',
        'Titik Kordinat',
        'Address'
    ]

    for gid in worksheet_gids:
        try:
            data_source = auth_to_google_v2(
                # json_auth_file='/opt/airflow/modules/lp_pos_photo/google_auth.json',
                json_auth_file='/Users/PARCEL/Downloads/testing_data_gsheet/google_auth.json',
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=gid
            )
            
            all_values = data_source.get_all_values()
            if not all_values:
                print(f"Warning: Sheet with GID {gid} is empty")
                continue
                
            headers = all_values[0]
            unique_headers = make_headers_unique(headers)
            data_rows = all_values[1:]
            
            df = pd.DataFrame(data_rows, columns=unique_headers)
            
            selected_columns = []
            for col in columns_to_keep:
                matching_cols = [c for c in df.columns if c.startswith(col)]
                selected_columns.extend(matching_cols)
            
            if not selected_columns:
                print(f"Warning: None of the specified columns were found in the sheet")
                print(f"Available columns: {', '.join(df.columns)}")
                continue
                
            df_filtered = df[selected_columns]

            # Find the Titik Kordinat column
            coord_column = [col for col in df_filtered.columns if col.startswith('Titik Kordinat')][0]

            # Create a temporary DataFrame to hold the split coordinates
            coord_df = pd.DataFrame(
                df_filtered[coord_column].apply(clean_and_split_coordinates).tolist(),
                columns=['Latitude', 'Longitude']
            )

            # Count null/invalid coordinates that were converted to 0.0
            null_coords = (coord_df['Latitude'] == "0.0") & (coord_df['Longitude'] == "0.0")
            if null_coords.any():
                print(f"Info: {null_coords.sum()} coordinates were null/invalid and set to 0.0")

            # Add the coordinate columns to the main DataFrame
            df_filtered['Latitude'] = coord_df['Latitude']
            df_filtered['Longitude'] = coord_df['Longitude']

            # Drop the original Titik Kordinat column
            df_filtered = df_filtered.drop(columns=[coord_column])

            # Rename all columns
            df_final_col = df_filtered.rename(columns={
                'POSCode'                   : 'pos_code',
                'POS Name'                  : 'pos_name',
                'Foto Lokasi Bagian Dalam'  : 'foto_lokasi_bagian_dalam',
                'Foto Lokasi Bagian Depan'  : 'foto_lokasi_bagian_depan',
                'Lokasi'                    : 'lokasi',
                'Kota/Kabupaten'            : 'kota_kabupaten',
                'Jenis Bangunan'            : 'jenis_bangunan',
                'Latitude'                  : 'latitude',
                'Longitude'                 : 'longitude',
                'Address'                   : 'alamat'
            })

            # Ensure latitude and longitude are strings
            df_final_col['latitude'] = df_final_col['latitude'].astype(str)
            df_final_col['longitude'] = df_final_col['longitude'].astype(str)

            # Filter out invalid POS codes
            initial_rows = len(df_final_col)
            df_final_col = df_final_col[df_final_col['pos_code'].apply(is_valid_pos_code)]
            filtered_rows = initial_rows - len(df_final_col)
            
            if filtered_rows > 0:
                print(f"Sheet 1: Filtered out {filtered_rows} rows with invalid POS codes")
            
            column_order = [
                    'pos_code', 
                    'foto_lokasi_bagian_dalam', 
                    'foto_lokasi_bagian_depan', 
                    'lokasi', 
                    'kota_kabupaten', 
                    'jenis_bangunan', 
                    'latitude', 
                    'longitude', 
                    'alamat',
                    'pos_name'
                ]
            
            df_final_col = df_final_col[column_order]

            # Save to CSV
            # output_path = f"/opt/airflow/modules/lp_pos_photo/dataset/pos_code_master_photo_data_1.csv"
            output_path = f"/Users/PARCEL/Downloads/testing_data_gsheet/dataset/pos_code_master_photo_data_1_test.csv"
            df_final_col.to_csv(output_path, sep=";", header=True, index=False)
            # print(f"Data types of columns:")
            # print(df_final_col.dtypes)
            # print(df_final_col.head())
            print(f"Successfully saved {len(df_final_col)} rows of data from sheet GID {gid} to {output_path}")
            
        except Exception as e:
            print(f"Error processing worksheet GID {gid}: {str(e)}")

def format_timestamp(timestamp):
    """
    Format timestamp from DD/MM/YYYY to DD-MM-YYYY and handle null values
    
    Args:
        timestamp: The timestamp to format
        
    Returns:
        str: Formatted timestamp
    """
    if pd.isna(timestamp) or str(timestamp).strip() == '' or str(timestamp).strip() == '-':
        return '31-12-9999'
    try:
        # Handle the case where timestamp might already contain hyphens
        timestamp = timestamp.replace('-', '/')
        # Split the date components
        day, month, year = timestamp.split('/')
        # Reconstruct with hyphens
        return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        return '31-12-9999'



def get_data_sheet_two():
    """
    Inserts data from a CSV file into a Google Spreadsheet.
    Handles duplicate headers by making them unique.
    Uses worksheet GID instead of index.
    """
    spreadsheet_id = "1VW0AFMpkjLVa1muXmV8JxTWaTUQ_6_SukNlxHssPdwQ"
    # Define the GIDs of the worksheets you want to process
    worksheet_gids = ["1868279837"]  # You can add more GIDs to this list

    # Define the columns we want to keep
    columns_to_keep = [
        'P.O.S Code',
        'FOTO 1 (TAMPAK DEPAN)',
        'FOTO 2 (TAMPAK DALAM)',
        'FOTO 4 (TAMBAHAN DETAIL LOKASI POS)',
        'Status Upload',
        'Timestamp'
    ]

    for gid in worksheet_gids:
        try:
            data_source = auth_to_google_v2(
                # json_auth_file='/opt/airflow/modules/lp_pos_photo/google_auth.json',
                json_auth_file='/Users/PARCEL/Downloads/testing_data_gsheet/google_auth.json',
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=gid
            )
            
            # Get all values including headers
            all_values = data_source.get_all_values()
            if not all_values:
                print(f"Warning: Sheet with GID {gid} is empty")
                continue
                
            # Get headers and make them unique
            headers = all_values[0]
            unique_headers = make_headers_unique(headers)
            
            # Get the data rows
            data_rows = all_values[1:]
            
            df = pd.DataFrame(data_rows, columns=unique_headers)
            
            # Find the columns that match our desired columns
            selected_columns = []
            for col in columns_to_keep:
                matching_cols = [c for c in df.columns if c.startswith(col)]
                selected_columns.extend(matching_cols)
            
            # Filter DataFrame to keep only the desired columns
            if not selected_columns:
                print(f"Warning: None of the specified columns were found in the sheet")
                print(f"Available columns: {', '.join(df.columns)}")
                continue
                
            df_filtered = df[selected_columns]

            df_final_col = df_filtered.rename(columns={
                'P.O.S Code': 'pos_code',
                'FOTO 2 (TAMPAK DALAM)': 'foto_lokasi_bagian_dalam',
                'FOTO 1 (TAMPAK DEPAN)': 'foto_lokasi_bagian_depan',
                'FOTO 4 (TAMBAHAN DETAIL LOKASI POS)': 'foto_tambahan_lokasi_pos',
                'Status Upload': 'status_upload',
                'Timestamp': 'timestamp'
            })

            # Filter out invalid POS codes before timestamp conversion
            initial_rows = len(df_final_col)
            df_final_col = df_final_col[df_final_col['pos_code'].apply(is_valid_pos_code)]
            filtered_rows = initial_rows - len(df_final_col)
            
            if filtered_rows > 0:
                print(f"Sheet 2: Filtered out {filtered_rows} rows with invalid POS codes")

            # Convert timestamp after filtering
            df_final_col['timestamp'] = df_final_col['timestamp'].apply(format_timestamp)
            # print(df_final_col)
            # df_cek_type = df_final_col
            # print(df_cek_type.dtypes)
            
            # Save to CSV
            # output_path = f"/opt/airflow/modules/lp_pos_photo/dataset/pos_code_master_photo_data_2.csv"
            output_path = f"/Users/PARCEL/Downloads/testing_data_gsheet/dataset/pos_code_master_photo_data_2_test.csv"
            df_final_col.to_csv(output_path, sep=";", header=True, index=False)
            print(f"Successfully saved {len(df_final_col)} rows of data from sheet GID {gid} to {output_path}")
            
        except Exception as e:
            print(f"Error processing worksheet GID {gid}: {str(e)}")

def get_data_sheet_three():
    """
    Inserts data from a CSV file into a Google Spreadsheet.
    Handles duplicate headers by making them unique.
    Uses worksheet GID instead of index.
    """
    spreadsheet_id = "1YniWV0eQVH5cMRrrFLjevFnqaRz1bDagJHQYcM_pDF0"
    worksheet_gids = ["706015433"]

    columns_to_keep = [
        'Poscode Genesis',
        'Cons Code',
        'Nama Konsol',
        'Keterangan'
    ]

    for gid in worksheet_gids:
        try:
            data_source = auth_to_google_v2(
                # json_auth_file='/opt/airflow/modules/lp_pos_photo/google_auth.json',
                json_auth_file='/Users/PARCEL/Downloads/testing_data_gsheet/google_auth.json',
                spreadsheet_id=spreadsheet_id,
                worksheet_gid=gid
            )
            
            all_values = data_source.get_all_values()
            if not all_values:
                print(f"Warning: Sheet with GID {gid} is empty")
                continue
                
            headers = all_values[0]
            unique_headers = make_headers_unique(headers)
            data_rows = all_values[1:]
            
            df = pd.DataFrame(data_rows, columns=unique_headers)
            
            selected_columns = []
            for col in columns_to_keep:
                matching_cols = [c for c in df.columns if c.startswith(col)]
                selected_columns.extend(matching_cols)
            
            if not selected_columns:
                print(f"Warning: None of the specified columns were found in the sheet")
                print(f"Available columns: {', '.join(df.columns)}")
                continue
                
            df_filtered = df[selected_columns]

            # Rename all columns
            df_final_col = df_filtered.rename(columns={
                'Poscode Genesis'           : 'pos_code_genesis',
                'Cons Code'                 : 'console_code',
                'Nama Konsol'               : 'console_name',
                'Keterangan'                : 'keterangan'
            })

            # Filter out invalid POS codes
            initial_rows = len(df_final_col)
            df_final_col = df_final_col[df_final_col['pos_code_genesis'].apply(is_valid_pos_code)]
            filtered_rows = initial_rows - len(df_final_col)
            
            if filtered_rows > 0:
                print(f"Sheet 3: Filtered out {filtered_rows} rows with invalid POS codes")
            
            column_order = [
                'pos_code_genesis',
                'console_code',
                'console_name',
                'keterangan'
                ]
            
            df_final_col = df_final_col[column_order]

            # Save to CSV
            # output_path = f"/opt/airflow/modules/lp_pos_photo/dataset/pos_code_master_photo_data_3.csv"
            output_path = f"/Users/PARCEL/Downloads/testing_data_gsheet/dataset/pos_code_master_photo_data_3_test.csv"
            df_final_col.to_csv(output_path, sep=";", header=True, index=False)
            # print(f"Data types of columns:")
            # print(df_final_col.dtypes)
            # print(df_final_col.head())
            print(f"Successfully saved {len(df_final_col)} rows of data from sheet GID {gid} to {output_path}")
            
        except Exception as e:
            print(f"Error processing worksheet GID {gid}: {str(e)}")

if __name__ == "__main__":
    get_data_sheet_one()
    get_data_sheet_two()
    get_data_sheet_three()