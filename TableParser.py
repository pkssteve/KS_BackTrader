import pandas as pd
import numpy as np
from bs4.element import NavigableString

def replaceMultiple(origin, strlist, replace):
    # if type(origin) != str:
    #     return origin

    for string in strlist:
            origin = origin.replace(string, replace)

    return origin


def pre_process_table(table):
    """
    INPUT:
        1. table - a bs4 element that contains the desired table: ie <table> ... </table>
    OUTPUT:
        a tuple of:
            1. rows - a list of table rows ie: list of <tr>...</tr> elements
            2. num_rows - number of rows in the table
            3. num_cols - number of columns in the table
    Options:
        include_td_head_count - whether to use only th or th and td to count number of columns (default: False)
    """
    rows = [x for x in table.find_all('tr')]

    num_rows = len(rows)

    # get an initial column count. Most often, this will be accurate
    num_cols = max([len(x.find_all(['th','td'])) for x in rows])

    # sometimes, the tables also contain multi-colspan headers. This accounts for that:
    header_rows_set = [x.find_all(['th', 'td']) for x in rows if len(x.find_all(['th', 'td']))>num_cols/2]

    num_cols_set = []

    for header_rows in header_rows_set:
        num_cols = 0
        for cell in header_rows:
            row_span, col_span = get_spans(cell)
            num_cols+=len([cell.getText()]*col_span)

        num_cols_set.append(num_cols)

    num_cols = max(num_cols_set)

    return (rows, num_rows, num_cols)


def get_spans(cell):
        """
        INPUT:
            1. cell - a <td>...</td> or <th>...</th> element that contains a table cell entry
        OUTPUT:
            1. a tuple with the cell's row and col spans
        """
        if cell.has_attr('rowspan'):
            rep_row = int(cell.attrs['rowspan'])
        else: # ~cell.has_attr('rowspan'):
            rep_row = 1
        if cell.has_attr('colspan'):
            rep_col = int(cell.attrs['colspan'])
        else: # ~cell.has_attr('colspan'):
            rep_col = 1

        return (rep_row, rep_col)

def process_rows(rows, num_rows, num_cols, manip_type = 0):
    """
    INPUT:
        1. rows - a list of table rows ie <tr>...</tr> elements
    OUTPUT:
        1. data - a Pandas dataframe with the html data in it
    """
    elements = []
    data = pd.DataFrame(np.ones((num_rows, num_cols))*np.nan)
    for i, row in enumerate(rows):
        try:
            col_stat = data.iloc[i,:][data.iloc[i,:].isnull()].index[0]
        except IndexError:
            print(i, row)

        for j, cell in enumerate(row.find_all(['td', 'th'])):
            rep_row, rep_col = get_spans(cell)

            #print("cols {0} to {1} with rep_col={2}".format    (col_stat, col_stat+rep_col, rep_col))
            #print("\trows {0} to {1} with rep_row={2}".format(i, i+rep_row, rep_row))

            #find first non-na col and fill that one
            while any(data.iloc[i,col_stat:col_stat+rep_col].notnull()):
                col_stat+=1

            curitems = []
            replaceVictim = ['\xa0', '\n', '\\u', '\u3000', ' ', '[', ']', '<span>', '</span>']
            if manip_type == 0:
                curitems = str(cell).split('<br/>')
            if len(curitems) <= 1:
                celltxt = cell.getText()
                celltxt = replaceMultiple(celltxt, replaceVictim, '')
            if len(curitems) > 1:
                curitems = list(map(lambda x: replaceMultiple(x, replaceVictim, ''), curitems))
                if '">' in curitems[0]:
                    curitems[0] = curitems[0][curitems[0].find('>') + 1:]
                curitems[-1] = curitems[-1].replace('</td>', '')
                if len(curitems) > 6:
                    elements.append(curitems[1:])
                celltxt = curitems[0]
            data.iloc[i:i+rep_row,col_stat:col_stat+rep_col] = celltxt
            if col_stat<data.shape[1]-1:
                col_stat+=rep_col
    if len(elements) > 0:
        data = data.append(pd.DataFrame(zip(*elements)))
        data.index = range(len(data))
    return data


def getDataFrame(HtmlTable, manipl_type = 0):
    rows, num_rows, num_cols = pre_process_table(HtmlTable)
    df_table = process_rows(rows, num_rows, num_cols, manipl_type)
    return df_table


def findTableforWord(tables, wordlist):
    if type(wordlist) != list:
        wordlist = [wordlist]
    foundWord = ''
    table_i = 0
    for table in tables:
        rows = [x for x in table.find_all('tr')]
        for row in rows:
            row_str = replaceMultiple(str(row), ['\xa0', '?', '\n', '\\u', ' ', '\u3000', '[', ']'], '')
            if '금융감독원' in row_str or '회계법인' in row_str or '보고서' in row_str or '회계기준' in row_str:
                break
            for word in wordlist:
                if word in row_str:
                    foundWord = word
                    break
            if foundWord != '':
                break
        if foundWord != '':
            return table_i, getDataFrame(table), foundWord
        table_i += 1

    return -1, None, ''