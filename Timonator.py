import os
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import matplotlib.pyplot as plt
import time
from tqdm import tqdm
from datetime import datetime, timedelta
global_file_name = str()
start_date = datetime
global_df = pd.DataFrame()


def set_timon_log_filename():
    global global_file_name
    root = tk.Tk()
    root.withdraw()
    print('Select a TiMon Logfile: ')
    global_file_name = filedialog.askopenfilename(title='Select TiMon log file')
    root.destroy()


def set_global_df(df):
    global global_df
    global_df = df


def read_and_clean_timon_log():
    global global_file_name
    df = pd.read_csv(global_file_name, sep=';')
    df.replace(',','.', regex=True, inplace=True)
    df['TIME'] = df['TIME'].astype('float64')
    convert_bitsets_to_int()
    return df


def set_start_date_var():
    global start_date
    date_list = [int(i) for i in global_file_name.split('.')[0].split('_')]
    start_date = datetime(date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5])
    print(f'Set start_date var to: {start_date}')


def create_datetime_column():
    global start_date
    global global_df
    if 'PLC_TIME(Timedate48)' in global_df.columns and 'PLC_TIME_CV(Enum2)' in global_df.columns:
        global_df['Time Date'] = pd.to_datetime(global_df['PLC_TIME(Timedate48)'], unit='s') + pd.to_timedelta(global_df['PLC_TIME_CV(Enum2)'], unit='h')
        global_df = global_df.set_index(['Time Date'])
    else:
        set_start_date_var()
        global_df['Time Date'] = global_df['TIME'].apply(lambda x: start_date + timedelta(seconds=x))
        global_df = global_df.set_index(['Time Date'])


def create_excel_format():
    global global_file_name
    global global_df
    root = tk.Tk()
    root.withdraw()
    global_df.to_csv(filedialog.asksaveasfilename(defaultextension='.csv',
                                                  title='EXCEL_Timon', filetypes=[('csv files', '*.csv')],
                                                  initialfile=f'EXCEL_{global_file_name}'))
    root.destroy()


def convert_bitsets_to_int():
    global global_df
    for col in global_df.columns:
        if 'Bitset' in col and global_df[col].dtypes == 'object':
            global_df[col] = global_df[col].apply(int, base=16)


def add_bitset_sub_columns(df):
    if 'ASDO_StsW(Bitset16)' in df.columns:
        df['Formation_OK'] = df['ASDO_StsW(Bitset16)'].apply(lambda x: Formation_OK(x))
    if 'PLC_EVR_BS1(Bitset8)' in df.columns:
        df['PLC_InauFinished'] = df['PLC_EVR_BS1(Bitset8)'].apply(lambda x: PLC_InauFinished(x))
    if 'HMI_SCREEN(Unsigned8)' in df.columns:
        df['Degraded_Mode'] = df['HMI_SCREEN(Unsigned8)'].apply(lambda x: degraded(x))
    if 'PLC_PIS_CMD1(Bitset8)' in df.columns:
        df['DoorSideA'] = df['PLC_PIS_CMD1(Bitset8)'].apply(lambda x: DoorSideA(x))
        df['DoorSideB'] = df['PLC_PIS_CMD1(Bitset8)'].apply(lambda x: DoorSideB(x))
    return df


def save_individual_plots_to_png(list_of_cols, df, remove_time_columns=True, folder_name='Timon_Plots'):
    """
    Takes a list and a data frame and makes a bunch of plots for each of the individual variables.
    Removes time/date columns from the list by default.
    Iterates over the columns to
    """
    os.mkdir(folder_name)
    if remove_time_columns:
        for col in list_of_cols:
            if col in ['PLC_TIME(Timedate48)', 'Time Date', 'TIME', 'PLC_TIME_CV(Enum2)']:
                list_of_cols.remove(col)

    for col in tqdm(list_of_cols):
        if col == 'PLC_MASTER_COACH(Unsigned16)':
            df[col].plot(figsize=(16, 4), legend=True, ylim=(15000, 15011))
            plt.savefig(folder_name, dpi=300, facecolor='w', edgecolor='w', orientation='landscape', format=None,
                        transparent=False, pad_inches=0.1)
            plt.close()
        elif col in ['Formation_OK', 'PLC_InauFinished', 'Degraded_Mode', 'DoorSideA', 'DoorSideB',
                     'HMI_CONFIRM_CMD(Boolean1)', 'HMI_RECALCULATE_CMD(Boolean1)'] or 'Boolean' in col:
            df[col].plot(figsize=(16, 4), legend=True, ylim=(0, 1))
            plt.savefig(folder_name, dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()
        else:
            df[col].plot(figsize=(16, 4), legend=True)
            plt.savefig(folder_name, dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()


def lifeword_plot(df: pd.DataFrame, file_name: str, lifeword: str):
    lw_search_list = lifeword.split('-')
    lw_list = []
    for search_word in lw_search_list:
        for col in df.columns:
            if search_word in col:
                lw_list.append(col)
    lw_df = df[lw_list]
    title_name = file_name.split('/')[-1]
    save_individual_plots_to_png(list_of_cols=lw_list, df=lw_df)
    lw_df.plot(subplots=True, figsize=(16, 8), legend=True, xlabel='Time Date',
               title=f'{lifeword} Lifeword :: {title_name}')
    plt.show()


def single_variable(df):
    choice = input('Type a variable to inspect: ')
    try:
        df[choice].plot(figsize=(16, 8), legend=True, xlabel='Time Date', title=choice)
        plt.show()
    except:
        print(f'{choice} does not exist, aborting. Typo?')
        time.sleep(3)


def Formation_OK(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to ASDO Formation data.
    """
    return int(f'{int(cell):016b}'[0])


def PLC_InauFinished(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to inauguration data.
    """
    return int(f'{int(cell):08b}'[3])


def degraded(cell):
    if cell == 100:
        return 1
    return 0


def LocoConnected(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to loco data.
    """
    return int(f'{int(cell):08b}'[-1])


def ClosedFormation(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to closed formation data.
    """
    return int(f'{int(cell):08b}'[-2])


def DoorSideA(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to Door side A data.
    """
    return int(f'{int(cell):08b}'[1])


def DoorSideB(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to Door side B data.
    """
    return int(f'{int(cell):08b}'[0])


def print_group():
    os.system('cls')
    print("""
     __  __
    |  \/  |  ___  _ __   _   _
    | |\/| | / _ \| '_ \ | | | |
    | |  | ||  __/| | | || |_| |
    |_|  |_| \___||_| |_| \__,_|
    
    1.  Look at FDS data
    2.  Look at GWE data
    3.  Look at HMI data
    4.  Look at Doors and ASDO
    5.  Look at PLC Variables
    6.  Look at EVR data
    7.  Inspect a single variable
    8.  Plot all variables to png
    9.  Create an Excel friendly version
        """)


def setup_dataframe():
    global global_df
    set_timon_log_filename()
    set_global_df(read_and_clean_timon_log())
    create_datetime_column()
    convert_bitsets_to_int()
    set_global_df(add_bitset_sub_columns(global_df))


def main():
    global global_df
    global global_file_name
    setup_dataframe()
    print_group()

    lifeword_list = {1: 'FDS', 2: 'GWE', 3: 'HMI', 4: 'DO1-DO2-ASDO', 5: 'PLC', 6: 'EVR'}
    choice = int(input('Select an option: '))
    if choice < 7:
        lifeword_plot(global_df, global_file_name, lifeword_list[choice])
    elif choice == 7:
        single_variable(global_df)
    elif choice == 8:
        save_individual_plots_to_png(list_of_cols=global_df.columns, df=global_df)
    elif choice == 9:
        create_excel_format()
    else:
        print('No selection made. Aborting.')
        time.sleep(3)

    os.system('cls')
    print("""
 _____  _                                  _
|_   _|(_) _ __ ___    ___   _ __    __ _ | |_   ___   _ __
  | |  | || '_ ` _ \  / _ \ | '_ \  / _` || __| / _ \ | '__|
  | |  | || | | | | || (_) || | | || (_| || |_ | (_) || |
  |_|  |_||_| |_| |_| \___/ |_| |_| \__,_| \__| \___/ |_| V1.0 alpha
                           ______
                         <((((((\\\\\\
                         /      . }\\
                         ;--..--._|}
      (\                 '--/\--'  )
       \\\\                | '-'  :'|
        \\\\               . -==- .-|
         \\\\               \.__.'   \--._
         [\\\\          __.--|       //  _/'--.
         \ \\\\       .'-._ ('-----'/ __/      \\
          \ \\\\     /   __>|      | '--.       |
           \ \\\\   |   \   |     /    /       /
            \ '\ /     \  |     |  _/       /
             \  \       \ |     | /        /
              \  \       \       /

    """)
    time.sleep(3)


if __name__ == "__main__":
    main()
