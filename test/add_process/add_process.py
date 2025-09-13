import pandas as pd
import configparser
import os


DATA_CSV = r"C:\Users\xzyoi\Desktop\python\task_schedule\schedules.csv"

# Configファイルを読み込む
config = configparser.ConfigParser()
config.read('./config.ini')
print()

# Configファイルの内容をリストに変換
data = []
for section in config.sections():
    # Section名が 'Process' である場合のみ処理する
    if section.startswith('Process'):
        process_data = {
            'Process ID': config[section].get('Process ID', ''),
            'Process Name': config[section].get('Process Name', ''),
            'Executable Path': config[section].get('Executable Path', ''),
            'Arguments': config[section].get('Arguments', ''),
            'Program Type': config[section].get('Program Type', ''),
            'Schedule Interval': config[section].get('Schedule Interval', ''),
            'Start Time': config[section].get('Start Time', ''),
            'End Time': config[section].get('End Time', ''),
            'Day of Week': config[section].get('Day of Week', ''),
            'Frequency': config[section].get('Frequency', ''),
            'Enabled': config[section].get('Enabled', ''),
            'Last Run Time': config[section].get('Last Run Time', ''),
            'Next Run Time': config[section].get('Next Run Time', ''),
            'Status': config[section].get('Status', ''),
            'Dependencies': config[section].get('Dependencies', ''),
            'Comments': config[section].get('Comments', '')
        }
        print(process_data)
        data.append(process_data)

# データを表示（オプション）
print("date print")
for item in data:
    print(item)

# pandas DataFrameに変換
new_df = pd.DataFrame(data)

# 既存のCSVファイルを読み込む
if os.path.exists(DATA_CSV):
    try:
        existing_df = pd.read_csv(DATA_CSV)
        print("既存のCSVファイルが正常に読み込まれました。")
    except pd.errors.EmptyDataError:
        print("既存のCSVファイルは空です。")
        existing_df = pd.DataFrame(columns=new_df.columns)
else:
    print("既存のCSVファイルが存在しません。新しいファイルを作成します。")
    existing_df = pd.DataFrame(columns=new_df.columns)

# NaNを空文字列に置き換え
existing_df.fillna('', inplace=True)

# 重複する'Executable Path'と'Arguments'を持つ行を除外
merged_df = pd.concat([existing_df, new_df], ignore_index=True)
deduplicated_df = merged_df.drop_duplicates(subset=['Executable Path', 'Arguments'], keep='last')


# CSVファイルに書き込む
#deduplicated_df.to_csv(DATA_CSV, index=False)

# 結果をCSVファイルに書き込む
try:
    deduplicated_df.to_csv(DATA_CSV, index=False)
    print(f"データが正常に {DATA_CSV} に書き込まれました。")
except Exception as e:
    print(f"エラーが発生しました: {e}")

# デバッグ情報の出力
print("新規データフレーム:")
print(new_df)


print("\n重複排除後のデータフレーム:")
print(deduplicated_df)
