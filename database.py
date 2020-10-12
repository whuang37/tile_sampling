import sqlite3
import csv
from shutil import copy
import os
import numpy as np
import pandas as pd
import h5py
import math
import constants
class Database:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        database_path = os.path.join(folder_path, "database.db")
        try:
            self.conn = sqlite3.connect(database_path)
            self.c = self.conn.cursor()
        except sqlite3.Error as error:
            print("Error while connecting to sqlite", error)
            self.conn.close()
            self.c.close()

    def close(self):
        self.conn.commit()
        self.c.close()
        self.conn.close()
    
    def initiate(self, array_path):
        create_table_query = '''CREATE TABLE IF NOT EXISTS annotations (TYPE TEXT NOT NULL,
                                                                        TILE_ID INTEGER NOT NULL,
                                                                        X INTEGER NOT NULL,
                                                                        Y INTEGER NOT NULL)'''
                                                                        
        self.c.execute(create_table_query)
        
        create_grid_query = '''CREATE TABLE IF NOT EXISTS tile (TILE_ID INTEGER NOT NULL, 
                                                                    FINISHED INTEGER)'''
                                                                    
        self.c.execute(create_grid_query)
        
        grid_completion = []
        for i in range (0, 100):
            x = (i, False)
            grid_completion.append(x)
            
        add_grid_query = '''INSERT INTO tile (TILE_ID, FINISHED)
                                                VALUES(?, ?)'''
        self.c.executemany(add_grid_query, grid_completion)
        
        self.close()
        
        # hdf5 conversion
        array = np.load(array_path)
        save_path = os.path.join(self.folder_path, "tile_array.h5")
        with h5py.File(save_path, "w") as hf:
            hf.create_dataset("tiles", data=array)
        
        
    def add_value(self, m_type, TILE_ID, x, y):
        data_values = (m_type, TILE_ID, x, y)
        
        insert_query = '''INSERT INTO annotations (TYPE, 
                                                   TILE_ID,
                                                   X,
                                                   Y)
                                                   values (?, ?, ?, ?)'''
        self.c.execute(insert_query, data_values)
        self.close()
        
    def delete_value(self, TILE_ID, x, y):
        data_values = (TILE_ID, x, y)
        delete_query = '''DELETE FROM annotations where TILE_ID = ? and x = ? and Y = ?'''
        self.c.execute(delete_query, data_values)
        self.close()
        
    def query_all_annotations(self):
        all_query = '''SELECT * from annotations'''
        self.c.execute(all_query)
        annotations = self.c.fetchall()
        return annotations
    
    def query_tile_annotations(self, tile_id):
        tile_query = '''SELECT * from annotations where TILE_ID = ?'''
        self.c.execute(tile_query, (tile_id,))
        tile_annotations = self.c.fetchall()
        
        return tile_annotations
    
    def finish_tile(self, tile_id, state):
        finish_tile_query = '''UPDATE tile SET FINISHED = ? WHERE TILE_ID = ?'''
        self.c.execute(finish_tile_query, (state, tile_id))
        result = self.c.fetchall()
        self.close()
        return result
    
    def get_tiles(self):
        get_tiles_query = '''SELECT * FROM tile'''
        self.c.execute(get_tiles_query)
        result = self.c.fetchall()
        self.close()
        return result
    
    def all_annotations_df(self):
        df = pd.read_sql_query('''SELECT TILE_ID, TYPE, count(TYPE) from annotations GROUP BY TILE_ID, TYPE''', self.conn)
        self.close()
        df = df.pivot(index = "TILE_ID", columns = "TYPE", values = "count(TYPE)")
        df = df.fillna(value=0)
        
        for key in constants.keys:
            if key not in df.columns:
                df[key] = 0
        return df
    
    def tile_annotation_values(self, tile_id):
        values_query = '''SELECT TYPE, count(TYPE) from annotations where TILE_ID = ? GROUP BY TYPE'''
        self.c.execute(values_query, (tile_id,))
        result = self.c.fetchall()
        self.close()
        
        values_dict = {}
        
        for value in result:
            values_dict[value[0]] = value[1]
        
        for key in constants.keys:
            if key not in values_dict:
                values_dict[key] = 0
        total = 0
        for x in values_dict.values():
            total += x
        
        values_dict["total"] = total
        return values_dict
    
if __name__ == "__main__":
    # Database(r"test").initiate(r"test\test_100_tile_stack.npy")
    # print(Database(r"test").all_annotations_df())
    print(Database(r"test").tile_annotation_values(0))