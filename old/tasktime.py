import subprocess
import os , sys
import pandas as pd 
from datetime  import datetime
# +----------------------------------------------------------------
# pandas option 
# +----------------------------------------------------------------
# 表示オプションを変更して、すべての行と列を表示する
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

# +----------------------------------------------------------------
#  csv 
# +----------------------------------------------------------------
DATA_CSV = r"C:\Users\xzyoi\Desktop\python\task_schedule\schedules.csv"

data_csv = pd.read_csv(DATA_CSV)

class TaskProcessor:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.load_csv()
        print(self.df)

    def load_csv(self):
        if os.path.exists(self.csv_path):
            try:
                self.df = pd.read_csv(self.csv_path)
                self.df.fillna('', inplace=True)  # NaNを空文字列に置き換え

                # 'Last Run Time'と'Next Run Time'を文字列として読み込み、変換
                self.df['Last Run Time'] = pd.to_datetime(self.df['Last Run Time'], errors='coerce').fillna(pd.NaT)
                self.df['Next Run Time'] = pd.to_datetime(self.df['Next Run Time'], errors='coerce').fillna(pd.NaT)
            except pd.errors.EmptyDataError:
                self.create_empty_dataframe()
        else:
            self.create_empty_dataframe()

    def create_empty_dataframe(self):
        self.df = pd.DataFrame(columns=[
            'Process ID', 'Process Name', 'Executable Path', 'Arguments', 'Program Type',
            'Schedule Interval', 'Start Time', 'End Time', 'Day of Week', 'Frequency', 
            'Enabled', 'Last Run Time', 'Next Run Time', 'Status', 'Dependencies', 'Comments'
        ])

    def save_csv(self):
        self.df.to_csv(self.csv_path, index=False)
        print(f"Updated data has been saved to {self.csv_path}")

    def execute_process(self, row):
        executable_path = row['Executable Path']
        arguments = str(row['Arguments']) if row['Arguments'] else ''
        program_type = row['Program Type']
        command = []

        if program_type == 'python':
            command = ['python', executable_path] + arguments.split()
        elif program_type == 'bash':
            command = ['bash', executable_path] + arguments.split()
        else:
            command = [executable_path] + arguments.split()

        # process directory setting 
        cwd = os.path.dirname(executable_path)
        print(f"Executing command: {command} in directory: {cwd}")

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=cwd)
            print(f"Process {row['Process Name']} executed successfully.")
            print(f"Command output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Process {row['Process Name']} failed to execute: {e}")
            print(f"Command stderr: {e.stderr}")
            return False
        except FileNotFoundError as e:
            print(f"Executable not found: {e}")
            return False

    def process_tasks(self):
        current_time = datetime.now()
        for index, row in self.df.iterrows():
            print(f"Processing row {index}: {row.to_dict()}")
            print(row['Enabled'] ,type(row['Enabled']))

            if row['Enabled'] :
                print(f"Process {row['Process Name']} is enabled.")
                last_run_time = row['Last Run Time']

                if pd.isna(last_run_time) or current_time > last_run_time:
                    print(f"Process {row['Process Name']} is due to run.")
                    if self.execute_process(row):
                        # 'Last Run Time'を更新
                        self.df.at[index, 'Last Run Time'] = current_time
                else:
                    print(f"Process {row['Process Name']} is not due to run.")
            else:
                print(f"Process {row['Process Name']} is not enabled.")

        print(self.df)

if __name__ == "__main__":
    task_processor = TaskProcessor(DATA_CSV )
    task_processor.process_tasks()
    task_processor.save_csv()