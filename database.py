import sqlite3
import csv
from shutil import copy
import os
import numpy as np
import pandas as pd
import h5py
import math
import constants
import matplotlib
import matplotlib.pyplot as plt
from PIL import Image

class Database:
    def __init__(self, parent_dir):
        self.parent_dir = parent_dir
        self.database_path = os.path.join(parent_dir, "database.db")
        try:
            self.conn = sqlite3.connect(self.database_path)
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
        save_path = os.path.join(self.parent_dir, "tile_array.h5")
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
        
    def export_all_annotations(self):
        all_query = '''SELECT * from annotations'''
        df = pd.read_sql_query(all_query, self.conn)
        self.close()
        array_path = os.path.join(self.parent_dir, "tile_array.hdf5")
        with h5py.File(array_path, "r") as hf:
            tile_indices = hf["tile_index"][0:100]
            dimensions = tuple(hf["rows-columns"][0:2])
        
        df["TILE_ID"] = tile_indices[df["TILE_ID"]]
        
        column_num = df["TILE_ID"] % dimensions[1]
        row_num = np.floor(df["TILE_ID"] / (dimensions[0] + 1))
        df["X"] = df["X"].multiply((column_num - 1) * constants.grid_dimensions[0])
        df["Y"] = df["Y"].multiply((row_num - 1) * constants.grid_dimensions[1])
    
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
    
    def format_df(self, df):
        total = df.sum(axis=1).cumsum() # total number with unaffected as a cumulative sum series
        df[["bi", "mu", "bimu"]] = df[["bi", "mu", "bimu"]].cumsum(axis=0)
        df["affected"] = df[["bi", "mu", "bimu"]].sum(axis=1)
        df = df.div(total, axis=0).multiply(100).round(2)
        # moving CE calc
        df["ce bi"] = df["bi"].rolling(window=10).std()
        df["ce mu"] = df["mu"].rolling(window=10).std()
        df["ce affected"] = df["affected"].rolling(window=10).std()
        # getting the 10 day std as a percentage of the current mean
        df[["ce bi", "ce mu", "ce affected"]] = df[["ce bi", "ce mu", "ce affected"]].div(df["affected"], axis=0).multiply(100)
        
        return df
    
    def check_completed(self):
        df = self.all_annotations_df()
        total_annotated = df.values.sum()
        df =self.format_df(df)
        # reopen connection as it was previously closed
        
        self.conn = sqlite3.connect(self.database_path)
        self.c = self.conn.cursor()
        finished_tiles = self.get_tiles()
        df["finished"] =  [finished_tiles[x][1] for x in df.index.tolist()]
        
        i = constants.min_perc
        j = constants.max_ce
        num_passed_tiles = len(df[(df["bi"] > i) & (df["mu"] > i) & (df["affected"] > i) & (df["finished"] == 1)][(df["ce bi"] < j) & (df["ce mu"] < j) & (df["ce affected"] < j)])
        if total_annotated >= constants.max_annotations:
            completed = True
        elif num_passed_tiles >= constants.passed_tiles_req:
            completed = True
        else:
            completed = False
        return completed, total_annotated, num_passed_tiles
    
    def create_graphs(self):
        matplotlib.use("Agg")
        df = self.format_df(self.all_annotations_df())
        
        total = df.sum(axis=1).cumsum() # total number with unaffected
        pie_sizes = df.iloc[-1, 0:4]
        fig, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(5, figsize=(4,15))
        
        ax1.pie(pie_sizes, explode=(0, 0, 0, .1), labels=["bi", "bi & mu", "mu", "un"], autopct="%1.1f%%"
                , startangle=90, radius=2.5)
        ax1.set_title("Annotation Breakdown", y=1.7)
        
        ax2.plot(total, df["bi"], label="Bi")
        ax2.set_title("Bi v Total Cells")
        ax2.set_ylabel("Percent Bi")
        ax2.set_xlabel("Total Cells Evaluated")
        
        ax3.plot(total, df["mu"], label="mu", color="orange")
        ax3.set_title("Mu v Total Cells")
        ax3.set_ylabel("Percent Mu")
        ax3.set_xlabel("Total Cells Evaluated")
        
        ax4.plot(total, df["affected"], label="total affected", color="green")
        ax4.set_title("Total Affected v Total Cells")
        ax4.set_ylabel("Percent Affected")
        ax4.set_xlabel("Total Cells Evaluated")
        
        ax5.plot(total, df["ce bi"], label="Bi")
        ax5.plot(total, df["ce mu"], label="mu", color="orange")
        ax5.plot(total, df["ce affected"], label="total affected", color="green")
        ax5.axhline(5, color="grey", alpha=.5, dashes=(1,1))
        ax5.set_title("Moving CE v Total Cells")
        ax5.set_ylabel("Moving CE Percentage")
        ax5.set_xlabel("Total Cells Evaluated")
        
        lines, labels = fig.axes[-1].get_legend_handles_labels()
        fig.legend(lines, labels, loc="upper center", bbox_to_anchor=(.5, .74), ncol=3)
        fig.tight_layout()
        canvas = plt.get_current_fig_manager().canvas
        canvas.draw()
        
        img = Image.frombytes("RGB", canvas.get_width_height(), canvas.tostring_rgb())
        img.save("test222222.png")
        plt.close(fig)
        
        return img

"""
type 
absolute x coord (from og image)
absolute y coord (from og image)

"""
if __name__ == "__main__":
    # Database(r"test").initiate(r"test\test_100_tile_stack.npy")
    print(Database(r"test").check_completed())
    # print(Database(r"test").tile_annotation_values(0))
    Database(r"test").export_all_annotations()