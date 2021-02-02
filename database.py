import sqlite3
import os
import numpy as np
import pandas as pd
import h5py
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
    
    def initiate(self, array_path, case_type):
        create_table_query = '''CREATE TABLE IF NOT EXISTS annotations (TYPE TEXT NOT NULL,
                                                                        TILE_ID INTEGER NOT NULL,
                                                                        X INTEGER NOT NULL,
                                                                        Y INTEGER NOT NULL)'''
                                                                        
        self.c.execute(create_table_query)
        
        create_grid_query = '''CREATE TABLE IF NOT EXISTS tile (TILE_ID INTEGER NOT NULL, 
                                                                    FINISHED INTEGER)'''
                                                                    
        self.c.execute(create_grid_query)
        
        create_case_type_query = '''CREATE TABLE IF NOT EXISTS type (TYPE_CASE TEXT NOT NULL)'''
        self.c.execute(create_case_type_query)
        
        add_type_query = '''INSERT INTO type (TYPE_CASE) VALUES(?)'''
        self.c.execute(add_type_query, (case_type, ))
        
        # # hdf5 conversion
        # array = np.load(array_path)
        # save_path = os.path.join(self.parent_dir, "tile_array.h5")
        # with h5py.File(save_path, "w") as hf:
        #     hf.create_dataset("tiles", data=array)
        new_array_path = os.path.join(self.parent_dir, "tile_array.hdf5")
        print(new_array_path)
        os.rename(array_path, new_array_path)
        
        with h5py.File(new_array_path, "r") as hf:
            array_size = len(hf["images"])
            
        grid_completion = [(i, False) for i in range(0, array_size)]
        
        add_grid_query = '''INSERT INTO tile (TILE_ID, FINISHED)
                                                VALUES(?, ?)'''
        self.c.executemany(add_grid_query, grid_completion)
        
        self.close()
        
    def set_case_type(self):
        self.__init__(self.parent_dir)
        self.case_type = self.get_type()
        
        if self.case_type == "biondi":
            self.ann_keys = constants.bi_keys
        else:
            self.ann_keys = constants.vac_keys
    
    def get_type(self):
        
        try:
            get_type_query = '''SELECT TYPE_CASE from type'''
            self.c.execute(get_type_query)
            type_case = self.c.fetchone()
            type_case = type_case[0]
        except:
            print("failed")
            type_case = "biondi"
        self.close()
        return type_case

    def update_hdf5(self, new_hdf5_path):
        new_hdf5_path = new_hdf5_path[:-1] # remove slash at the end
        new_array_path = os.path.join(self.parent_dir, "tile_array.hdf5") # incase slashes are wrong
        print(new_array_path)
        if os.path.exists(new_array_path):
            os.remove(new_array_path)
        else:
            print("path does not exist")
            return 1
        
        os.rename(new_hdf5_path, new_array_path)
        with h5py.File(new_array_path, "r") as hf:
            array_size = len(hf["images"])
            
        old_size = self.get_num_tiles()
        
        additional_tiles = [(i, False) for i in range(old_size, array_size)]
        self.conn = sqlite3.connect(self.database_path)
        self.c = self.conn.cursor()
        
        add_grid_query = '''INSERT INTO tile (TILE_ID, FINISHED)
                                                VALUES(?, ?)'''
        self.c.executemany(add_grid_query, additional_tiles)
        
        self.close()
        
    def get_num_tiles(self):
        get_num_tiles_query = '''SELECT COUNT(*) FROM tile'''
        self.c.execute(get_num_tiles_query)
        num = self.c.fetchall()
        self.close()
        
        return num[0][0]
    
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
        
    def export_all_annotations(self, new_folder_path, case_name):
        all_query = '''SELECT * from annotations'''
        df = pd.read_sql_query(all_query, self.conn)
        
        unadjusted_grid_save_path = os.path.join(new_folder_path, f"{case_name}-unadjusted-grids.csv")
        df.to_csv(unadjusted_grid_save_path)
        array_path = os.path.join(self.parent_dir, "tile_array.hdf5")
        with h5py.File(array_path, "r") as hf:
            tile_indices = hf["tile_index"][0:]
            dimensions = tuple(hf["rows-columns"][0:2])
        
        df["TILE_ID"] = tile_indices[df["TILE_ID"]]
        
        column_num = df["TILE_ID"] % dimensions[1]
        row_num = df["TILE_ID"].floordiv(dimensions[1])
        df["X"] = (column_num * constants.grid_dimensions[0]) + df["X"]
        df["Y"] = (row_num * constants.grid_dimensions[1]) + df["Y"]
        info_df = self.format_df(self.all_annotations_df())
        
        adjusted_grid_save_path = os.path.join(new_folder_path, f"{case_name}-adjusted-grids.csv")
        inf_save_path = os.path.join(new_folder_path, f"{case_name}-info.csv")
        
        df.to_csv(adjusted_grid_save_path)
        info_df.to_csv(inf_save_path)
        
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
        self.get_type()
        self.__init__(self.parent_dir) # reopens the connection
        
        df = pd.read_sql_query('''SELECT TILE_ID, TYPE, count(TYPE) from annotations GROUP BY TILE_ID, TYPE''', self.conn)
        self.close()
        df = df.pivot(index = "TILE_ID", columns = "TYPE", values = "count(TYPE)")
        df = df.fillna(value=0)
        
        for key in self.ann_keys:
            if key not in df.columns:
                df[key] = 0
        return df
    
    def tile_annotation_values(self, tile_id):
        self.set_case_type()
        self.__init__(self.parent_dir) # reopens the connection
        
        values_query = '''SELECT TYPE, count(TYPE) from annotations where TILE_ID = ? GROUP BY TYPE'''
        self.c.execute(values_query, (tile_id,))
        result = self.c.fetchall()
        self.close()
        
        values_dict = {}
        
        for value in result:
            values_dict[value[0]] = value[1]
        
        for key in self.ann_keys:
            if key not in values_dict:
                values_dict[key] = 0
        total = 0
        for x in values_dict.values():
            total += x
        
        values_dict["total"] = total
        return values_dict
    
    def format_df(self, df):
        self.set_case_type()
        self.__init__(self.parent_dir) # reopens the connection
        
        df[self.ann_keys] = df[self.ann_keys].cumsum(axis=0)
        df["affected"] = df[[self.ann_keys[1], self.ann_keys[2], self.ann_keys[3]]].sum(axis=1)
        df["total"] = df [self.ann_keys].sum(axis=1) # total number with unaffected as a cumulative sum series
        df[[f"{self.ann_keys[1]} %", 
            f"{self.ann_keys[2]} %", 
            f"{self.ann_keys[3]} %", 
            "affected %"]] = (df[[self.ann_keys[1], 
                                  self.ann_keys[2], 
                                  self.ann_keys[3], "affected"]].div(df["total"], axis=0).multiply(100)).round(2)
        # add bimu % to bi % and mu %
        # fix later
        
        # add bimu
        if self.case_type == "biondi":
            df[["bi %", "mu %"]] = df[["bi %", "mu %"]].add(df["bimu %"], axis=0)
        
        # moving CE calc
        df[f"ce {self.ann_keys[1]} %"] = df[f"{self.ann_keys[1]} %"].rolling(window=10).std()
        df[f"ce {self.ann_keys[2]} %"] = df[f"{self.ann_keys[2]} %"].rolling(window=10).std()
        df["ce affected %"] = df["affected %"].rolling(window=10).std()
        # getting the 10 day std as a percentage of the current mean for each classification
        df[f"ce {self.ann_keys[1]} %"] = df[f"ce {self.ann_keys[1]} %"].div(df[f"{self.ann_keys[1]} %"]) * 100
        df[f"ce {self.ann_keys[2]} %"] = df[f"ce {self.ann_keys[2]} %"].div(df[f"{self.ann_keys[2]} %"]) * 100
        df["ce affected %"] = df["ce affected %"].div(df["affected %"]) * 100
        
        return df
    
    def check_completed(self):
        self.set_case_type()
        self.__init__(self.parent_dir) # reopens the connection
        
        df = self.all_annotations_df()
        total_annotated = df.values.sum()
        df =self.format_df(df)
        df = df.iloc[-constants.passed_tiles_req:, :]
        # reopen connection as it was previously closed
        self.conn = sqlite3.connect(self.database_path)
        self.c = self.conn.cursor()
        finished_tiles = self.get_tiles()
        df["finished"] =  [finished_tiles[x][1] for x in df.index.tolist()]
        
        i = constants.min_perc
        j = constants.max_ce
        try:
            bi = df[f"{self.ann_keys[1]} %"].iloc[-1]
            mu = df[f"{self.ann_keys[2]} %"].iloc[-1]
        except:
            bi = 0
            mu = 0
            
            
        if (bi > i) & (mu > i):
            num_passed_tiles = len(df[(df["finished"] == 1) & (df[f"ce {self.ann_keys[1]} %"] < j) & (df[f"ce {self.ann_keys[1]} %"] < j)])
        elif (bi > i) & (mu <= i):
            num_passed_tiles = len(df[(df["finished"] == 1) & (df[f"ce {self.ann_keys[1]} %"] < j)])
        elif (mu > i) & (bi <= i):
            num_passed_tiles = len(df[(df["finished"] == 1) & (df[f"ce {self.ann_keys[2]} %"] < j)])
        else:
            num_passed_tiles = 0
        
        print(df)
        # 10 recent in a row
        
        if total_annotated >= constants.max_annotations:
            completed = True
        elif num_passed_tiles == constants.passed_tiles_req:
            completed = True
        else:
            completed = False
        return completed, total_annotated
    
    def create_graphs(self):
        self.set_case_type()
        self.__init__(self.parent_dir) # reopens the connection
        
        matplotlib.use("Agg")
        df = self.format_df(self.all_annotations_df())
        
        total = df["total"] # total number with unaffected
        try:
            pie_sizes = df.iloc[-1, 0:4]
        except:
            pie_sizes = (0,0,0,0)
        fig, (ax1,ax2,ax3,ax4,ax5) = plt.subplots(5, figsize=(4,15))
        
        ax1.pie(pie_sizes, explode=(0, 0, 0, .1), labels=[f"{self.ann_keys[1]} {pie_sizes[0]}", 
                                                          f"{self.ann_keys[3]} {pie_sizes[1]}", 
                                                          f"{self.ann_keys[2]} {pie_sizes[2]}", 
                                                          f"{self.ann_keys[0]} {pie_sizes[3]}"], autopct="%1.1f%%",
                startangle=90, radius=1)
        ax1.set_title("Annotation Breakdown", y=1.7)
        
        ax2.plot(total, df[f"{self.ann_keys[1]} %"], label=self.ann_keys[1])
        ax2.set_title(f"{self.ann_keys[1]} v Total Cells")
        ax2.set_ylabel(f"Percent {self.ann_keys[1]}")
        ax2.set_xlabel("Total Cells Evaluated")
        
        ax3.plot(total, df[f"{self.ann_keys[2]} %"], label=self.ann_keys[1], color="orange")
        ax3.set_title(f"{self.ann_keys[2]} v Total Cells")
        ax3.set_ylabel(f"Percent {self.ann_keys[2]}")
        ax3.set_xlabel("Total Cells Evaluated")
        
        ax4.plot(total, df["affected %"], label="total affected", color="green")
        ax4.set_title("Total Affected v Total Cells")
        ax4.set_ylabel("Percent Affected")
        ax4.set_xlabel("Total Cells Evaluated")
        
        ax5.plot(total, df[f"ce {self.ann_keys[1]} %"], label=self.ann_keys[1])
        ax5.plot(total, df[f"ce {self.ann_keys[2]} %"], label=self.ann_keys[2], color="orange")
        ax5.plot(total, df["ce affected %"], label="total affected", color="green")
        ax5.axhline(5, color="grey", alpha=.5, dashes=(1,1))
        ax5.set_title("Moving CE v Total Cells")
        ax5.set_ylabel("Moving CE Percentage")
        ax5.set_xlabel("Total Cells Evaluated")
        ax5.set(ylim=(0, 25))
        
        lines, labels = fig.axes[-1].get_legend_handles_labels()
        fig.legend(lines, labels, loc="upper center", bbox_to_anchor=(.5, .74), ncol=3)
        fig.tight_layout()
        canvas = plt.get_current_fig_manager().canvas
        canvas.draw()
        
        img = Image.frombytes("RGB", canvas.get_width_height(), canvas.tostring_rgb())
        plt.close(fig)
        
        return img

"""
type 
absolute x coord (from og image)
absolute y coord (from og image)

"""
if __name__ == "__main__":
    # Database(r"test").initiate(r"test\test_100_tile_stack.npy")
    # Database(r"test").format_df(Database(r"test").all_annotations_df)
    # print(Database(r"test").tile_annotation_values(0))
    Database(r"testingaddition").update_hdf5("xx.hdf5")