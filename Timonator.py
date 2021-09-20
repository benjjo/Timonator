import os
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
global_file_name = str()
start_date = datetime
global_df = pd.DataFrame()
list_of_bitsets = []
mvb_dictionary = {}
folder_name = 'Timon_Plots'


def set_timon_log_filename():
    """
    Prompts the user to select a timon log file.
    Note that this must be a raw timon log file generated from the timon_embedded.xml file.
    """
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
    """
    Reads in the data from the pre selected timon log file. Some minor character changes made to help with
    data types later on down the track.
    Pre-condition: global_file_name contains a file name.

    :return: pd.DataFrame() object
    """
    global global_file_name
    df = pd.read_csv(global_file_name, sep=';')
    df.replace(',', '.', regex=True, inplace=True)
    df['TIME'] = df['TIME'].astype('float64')
    convert_bitsets_to_int()
    return df


def set_start_date_var():
    """
    Updates the start_date variable using the name of the timon file.
    By default the timon log will name the timon log file using the time
    and date from the TCMS HMI. If there is no PLC_TIME variable recorded,
    start_date will be used in conjunction with the TIME (seconds since
    start of recording) to make a time date index.
    """
    global start_date
    global global_file_name
    file_name = global_file_name.split('/')[-1]
    date_list = [int(i) for i in file_name.split('.')[0].split('_')]
    start_date = datetime(date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5])
    print(f'Set start_date var to: {start_date}')


def set_mvb_dictionary():
    """
    Looks for a file in the working directory called 'mvb_list.ben'. Failing that the
    function will prompt the user to continue to search for a file locally.
    Once located, the global dictionary is updated with the contents of the file.
    """
    global mvb_dictionary
    global list_of_bitsets
    try:
        mvb_dictionary = eval(open('mvb_list.ben', 'r').read())
    except FileNotFoundError:
        print('MVB List not present in working directory.')
        choice = input('Do you wish to create one? [Y to continue]')
        if choice in 'YyYESYesyes':
            update_mvb_dictionary(list_of_bitsets, make_bitset_df())
        else:
            abort_protocol()


def user_defined_mvb_list():
    """
    Prompts the user to identify an updated MVB list of type xlsx.

    :return: str
    """
    root = tk.Tk()
    root.withdraw()
    print('Select the E39_CALEDONIAN_MVB_Seated.xlsx Document: ')
    mvb_file_name = filedialog.askopenfilename(title='Select E39_CALEDONIAN_MVB_Seated.xlsx Document')
    root.destroy()
    return mvb_file_name


def create_datetime_column():
    """
    Creates a index based on a Date Time column. This column is either created from
    a unix time stamp or calculated using the seconds since start of recording [TIME] column.
    """
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
    """
    Prompts the user to enter a location to save an Excel friendly version of the timon
    csv log. This file will include dates in a human readable format as opposed to the
    standard timon TIME in seconds or UNIX seconds.
    """
    global global_file_name
    global global_df
    root = tk.Tk()
    root.withdraw()
    excel_name = global_file_name.split('/')[-1]
    global_df.to_csv(filedialog.asksaveasfilename(defaultextension='.csv',
                                                  title='EXCEL_Timon', filetypes=[('csv files', '*.csv')],
                                                  initialfile=f'EXCEL_{excel_name}'))
    root.destroy()


def convert_bitsets_to_int():
    """
    Inspects the column headings and checks for the bitset data and
    converts the hexadecimal data to decimal.
    """
    global global_df
    for col in global_df.columns:
        if 'Bitset' in col and global_df[col].dtypes == 'object':
            global_df[col] = global_df[col].apply(int, base=16)


def add_bitset_sub_columns(df, mega_mvb_dic, bitset):
    """
    Adds the individual bitset sub-columns to the df.
    If they are a bitset value, they will be plotted.

    :return: pd.DataFrame() object
    """
    global folder_name
    if bitset in df.columns:
        bitset = bitset.split('(')[0]
        if bitset in mega_mvb_dic:
            for bitset_sub_col in mega_mvb_dic[bitset]:
                bit = mega_mvb_dic[bitset][bitset_sub_col]
                print('\n :::: ' + df[bitset_sub_col] + ' ::::\n')
                df[bitset_sub_col] = df[mega_mvb_dic[bitset]].apply(lambda x: get_bitset_value(x, bit))

            df[bitset].plot(figsize=(16, 4), legend=True, ylim=(0, 1), linewidth=2)
            plt.savefig(f'{folder_name}/{bitset}.png', dpi=300, facecolor='w', edgecolor='w',
                        orientation='landscape', format=None, transparent=False, pad_inches=0.1)
    else:
        print('Something went terribly wrong. Perhaps the mvb_list.ben is empty.')
        abort_protocol()

    return df


def make_local_plots_directory():
    """
    Creates a folder in the
    """
    global folder_name
    try:
        os.mkdir(folder_name)
    except FileExistsError:
        print(f'Directory {folder_name} exists, you may overwrite data.')
        time.sleep(3)
        os.system('cls')
    except PermissionError:
        print('You are running this script in a folder that wont allow you to write to it.')
        abort_protocol()


def save_individual_plots_to_png(list_of_cols, df, remove_time_columns=True):
    """
    Takes a list and a data frame and makes a bunch of plots for each of the individual variables.
    Removes time/date columns from the list by default.
    Iterates over the columns to find the variables to be displayed.
    """
    global folder_name
    global mvb_dictionary
    set_mvb_dictionary()

    if not os.path.exists(folder_name):
        make_local_plots_directory()

    if remove_time_columns:
        for col in list_of_cols:
            if 'TIME' in col:
                print(f'removing {col}')
                list_of_cols.remove(col)

    for col in list_of_cols:
        if col == 'PLC_MASTER_COACH(Unsigned16)':
            df[col].plot(figsize=(16, 4), legend=True, ylim=(15001, 15011), linewidth=5)
            plt.savefig(f'{folder_name}/{col}.png', dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()
        elif 'Boolean' in col:
            df[col].plot(figsize=(16, 4), legend=True, ylim=(0, 1), linewidth=2)
            plt.savefig(f'{folder_name}/{col}.png', dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()
        elif 'Bitset' in col and col.split('(')[0] in mvb_dictionary:
            plot_bitsets(df, mvb_dictionary, col)
            plt.close()
        elif 'Enum2' in col:
            df[col].plot(figsize=(16, 4), legend=True, ylim=(0, 3), linewidth=2)
            plt.savefig(f'{folder_name}/{col}.png', dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()
        elif 'TIME' in col:
            pass
        else:
            df[col].plot(figsize=(16, 4), legend=True)
            plt.savefig(f'{folder_name}/{col}.png', dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                        format=None, transparent=False, pad_inches=0.1)
            plt.close()


def plot_bitsets(df, mvb_dic, key):
    global folder_name
    sub_key = key.split('(')[0]
    if sub_key in mvb_dic and key in str(df.columns):
        for col in mvb_dic[sub_key]:
            if 'reserve' not in col:
                counter = 0
                new_col = f'{sub_key}_{col}'
                df[new_col] = df[key].apply(lambda x: get_bitset_value(x, mvb_dic[sub_key][col]))
                df[new_col].plot(figsize=(16, 4), legend=True, ylim=(0, 1), linewidth=2)
                while os.path.exists(f'{folder_name}\\{new_col}'):
                    col = f'{new_col}{str(counter)}'
                    counter += 1
                plt.savefig(f'{folder_name}/{new_col}.png', dpi=300, facecolor='w', edgecolor='w',
                            orientation='landscape', format=None, transparent=False, pad_inches=0.1)
                plt.close()


def lifeword_plot(df: pd.DataFrame, file_name: str, lifeword: str):
    """
    Uses a keyword to search through the data and find a bunch of variables
    that fit that criteria.
    Plots the data do a folder in the local directory.
    """
    global folder_name
    if not os.path.exists(folder_name):
        make_local_plots_directory()

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


def plot_a_single_variable(df, get_choices=True, col=None):
    """
    Spits out a list of variables from the main Pandas Data Frame containing
    all of the TiMon log data. This is list of the headings from the data frame
    and one of these variables can be used for interrogation.
    The user is be prompted to enter one of these variables to inspect.
    """
    global folder_name
    if not os.path.exists(folder_name):
        make_local_plots_directory()

    if get_choices:
        os.system('cls')
        for col in df.columns:
            print(col)
        col = input('\nType a variable to inspect: ')

    try:
        df[col].plot(figsize=(16, 8), legend=True, xlabel='Time Date', title=col)
        plt.savefig(f'{folder_name}/{col}.png', dpi=300, facecolor='w', edgecolor='w', orientation='landscape',
                    format=None, transparent=False, pad_inches=0.1)
        plt.show()
    except ValueError:
        print(f'{col} does not exist. Typo?')
        abort_protocol()


def inspect_a_single_variable(df):
    """
    Spits out a list of variables from the main Pandas Data Frame containing
    all of the TiMon log data. This is list of the headings from the data frame
    and one of these variables can be used for interrogation.
    The user is be prompted to enter one of these variables to inspect.
    """
    os.system('cls')
    for col in df.columns:
        print(col)

    col = input('\nType a variable to inspect: ')

    try:
        df[col].plot(figsize=(16, 8), legend=True, xlabel='Time Date', title=col)
        plt.show()
    except KeyError:
        print(f'{col} does not exist. Typo?')
        abort_protocol()


def make_bitset_df():
    """
    Creates and returns a Pandas Data Frame with the bitset data.
    This will call the get_mvb_list function which will prompt the user
    to identify an appropriate MVB list of type xlsx.

    :return: pd.DataFrame() object
    """
    global global_df
    bitsetdf = global_df.copy()
    mvb_list = user_defined_mvb_list()
    cols = ['VarId', 'VarType', 'Comment0', 'Comment1']
    bitsetdf = pd.read_excel(mvb_list, sheet_name='Variables', header=0, usecols=cols)
    bitsetdf['VarId'].ffill(inplace=True)
    bitsetdf['VarType'].ffill(inplace=True)
    bitsetdf = bitsetdf.dropna(how='all')
    bitsetdf = bitsetdf[bitsetdf.VarType.str.contains('BITSET', case=True)]
    # Get indexes where name column doesn't have value john
    indexNames = bitsetdf[(bitsetdf['Comment0'] == 'Bits')].index
    # Delete these row indexes from dataFrame
    bitsetdf.drop(indexNames, inplace=True)
    bitsetdf.reset_index(inplace=True)

    return bitsetdf


def map_bitrange_to_value(bitset_variable, bit_df):
    """
    Maps the bitset range of bits to the associated variable name. i.e. {'Bit 1':0, 'Bit 2':1}

    :return: dictionary
    """
    bitset_dic = {}
    for row_num in bit_df.loc[bit_df['VarId'] == bitset_variable, 'Comment0'].index:
        bitset_dic[bit_df.loc[bit_df.index[row_num], 'Comment1']] = bit_df.loc[bit_df.index[row_num], 'Comment0']
    return bitset_dic


def set_list_of_bitsets(bit_df):
    """
    Sets the unique id set of bitsets to the global var.
    """
    global list_of_bitsets
    list_of_bitsets = bit_df['VarId'].unique()


def dic_of_all_bitsets_to_bitrange(bitset_list, bit_df):
    """
    Maps the bitset dictionary to a Var ID. i.e. {'Var 1': {'Bit 1':0, 'Bit 2':1}, 'Var 2': {'Bit 1':0, 'Bit 2':1}}

    :return: dictionary
    """
    mvb_dict = {}
    for bitset in bitset_list:
        mvb_dict[bitset] = map_bitrange_to_value(bitset, bit_df)
    return mvb_dict


def update_mvb_dictionary(bitset_list, bit_df):
    """
    Requests the user to input a new list of MVB data from a file of type xlsx.
    """
    global list_of_bitsets
    root = tk.Tk()
    root.withdraw()
    file_out = filedialog.asksaveasfilename(defaultextension='.ben',
                                            title='Update MVB list', filetypes=[('Benjo files', '*.ben')],
                                            initialfile='mvb_list.ben')
    root.destroy()
    print('Please wait. This may take a minute or two...')

    if not bitset_list:
        set_list_of_bitsets(bit_df)
        bitset_list = list_of_bitsets

    time.sleep(3)
    mega_mvb_dict = dic_of_all_bitsets_to_bitrange(bitset_list, bit_df)
    print(f'{len(mega_mvb_dict)} variables with corresponding bitsets added.')
    time.sleep(1)
    # file_out = 'mvb_list.ben'
    try:
        with open(file_out, 'w') as fout:
            fout.write(str(mega_mvb_dict).replace(', nan: nan', ''))
    except (FileExistsError, PermissionError):
        print(f'Failed to overwrite file {file_out}.')
        abort_protocol()

    print('SUCCESS!')
    set_mvb_dictionary()


def abort_protocol():
    print("""
        _     ____    ___   ____   _____  ___  _   _   ____
       / \   | __ )  / _ \ |  _ \ |_   _||_ _|| \ | | / ___|
      / _ \  |  _ \ | | | || |_) |  | |   | | |  \| || |  _
     / ___ \ | |_) || |_| ||  _ <   | |   | | | |\  || |_| |
    /_/   \_\|____/  \___/ |_| \_\  |_|  |___||_| \_| \____|

    """)
    time.sleep(3)
    quit()


def plot_bitset_data(list_of_cols, df, remove_time_columns=True):
    """
    Plots the bitset data.
    """
    global folder_name
    global mvb_dictionary
    set_mvb_dictionary()

    if not os.path.exists(folder_name):
        make_local_plots_directory()

    if remove_time_columns:
        for col in list_of_cols:
            if 'TIME' in col:
                print(f'removing {col}')
                list_of_cols.remove(col)
    print('Populating Timon_Plots folder. This may take some time with big files.')
    for col in list_of_cols:
        if 'Bitset' in col and col.split('(')[0] in mvb_dictionary:
            plot_bitsets(df, mvb_dictionary, col)
            plt.close()


def get_bitset_value(cell_value, bit):
    """
    Returns the bit value associated with the variable.
    """
    try:
        return int(f'{int(cell_value):016b}'[::-1][bit])
    except IndexError:
        return 0


def ASDO_Formation_OK(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to ASDO Formation data.
    """
    return int(f'{int(cell):016b}'[-1])


def PLCNullSpeed(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to inauguration data.
    """
    return int(f'{int(cell):08b}'[0])


def PLC_InauFinished(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to inauguration data.
    """
    return int(f'{int(cell):08b}'[4])


def ASDO_Overrided(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to inauguration data.
    """
    return int(f'{int(cell):08b}'[6])


def TimeSync(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to inauguration data.
    """
    return int(f'{int(cell):08b}'[7])


def degraded(cell):
    if cell == 100:
        return 1
    return 0


def LocoConnected(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to loco data.
    """
    return int(f'{int(cell):08b}'[0])


def ClosedFormation(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to closed formation data.
    """
    return int(f'{int(cell):08b}'[1])


def Power_Off(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to closed formation data.
    """
    return int(f'{int(cell):08b}'[3])


def ZeroSpeed(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to closed formation data.
    """
    return int(f'{int(cell):08b}'[5])


def DoorSideA(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to Door side A data.
    """
    return int(f'{int(cell):08b}'[6])


def DoorSideB(cell):
    """
    Converts cell into binary bits. Returns the selected bit related to Door side B data.
    """
    return int(f'{int(cell):08b}'[7])


def print_group():
    os.system('cls')
    print("""
     __  __
    |  \/  |  ___  _ __   _   _
    | |\/| | / _ \| '_ \ | | | |
    | |  | ||  __/| | | || |_| |
    |_|  |_| \___||_| |_| \__,_|
    
    1.  Look at data using a keyword search
    2.  Inspect a single variable
    3.  Plot all variables to png
    4.  Create an Excel friendly version
    5.  Plot the available bitsets
    6.  Update the MVB list with a new version 
        [Defaults to V2.34]
        """)


def setup_dataframe():
    global global_df
    set_timon_log_filename()
    set_global_df(read_and_clean_timon_log())
    create_datetime_column()
    convert_bitsets_to_int()
    set_global_df(global_df)


def main():
    global global_df
    global global_file_name
    global list_of_bitsets
    setup_dataframe()
    print_group()

    try:
        choice = int(input('Select an option: '))
        if choice == 1:
            os.system('cls')
            print("""
            Input a search word to look for in the timon log.
            Here's a few suggestions: FDS, GWE, HMI, PLC, ASDO, EVR, DO1, DO2
            If you want to add a few options at once, separate the values using the dash -
            eg. DO1-DO2-ASDO
            """)
            search_term = input('Input a search term here: ')
            lifeword_plot(global_df, global_file_name, search_term)
        elif choice == 2:
            plot_a_single_variable(global_df)
        elif choice == 3:
            current_list_of_cols = list(global_df.columns)
            save_individual_plots_to_png(list_of_cols=current_list_of_cols, df=global_df)
        elif choice == 4:
            create_excel_format()
        elif choice == 5:
            current_list_of_cols = list(global_df.columns)
            plot_bitset_data(list_of_cols=current_list_of_cols, df=global_df)
        elif choice == 6:
            update_mvb_dictionary(list_of_bitsets, make_bitset_df())
        else:
            print('No selection made. Aborting.')
            time.sleep(3)
    except ValueError:
        print('Poor selection choice.')
        abort_protocol()

    os.system('cls')
    print("""
 _____  _                                  _
|_   _|(_) _ __ ___    ___   _ __    __ _ | |_   ___   _ __
  | |  | || '_ ` _ \  / _ \ | '_ \  / _` || __| / _ \ | '__|
  | |  | || | | | | || (_) || | | || (_| || |_ | (_) || |
  |_|  |_||_| |_| |_| \___/ |_| |_| \__,_| \__| \___/ |_| V1.0 beta
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



  ** Ben McGuffog 2021
    """)
    time.sleep(3)


if __name__ == "__main__":
    main()
