import csv
import os


###
# This is very specific to one use case but this how this can be generally done
###
with open("TimeSheet.csv") as times_csv:
    timesheet_reader = csv.reader(times_csv)
    for row in timesheet_reader:

        tags = ""
        # tags are in extra columns
        for tag in row[7:-1]:
            if tag:
                tags += f"\"{tag.strip()}\""
            else:
                # assumption: no empty cells
                break

            #print(tag)
        print(f"timew track {row[0]}T{row[1]} - {row[0]}T{row[2]} {tags}")
        os.system(f"timew track {row[0]}T{row[1]} - {row[0]}T{row[2]} {tags}")
