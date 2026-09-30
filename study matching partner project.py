# Study Partner Matching Project
# This program reads the Google Form CSV. Matches students into
# study pairs based on their subject marks, free time and study style

import csv
import os
import re

# how much each factor counts towards the final score
COMPLEMENT_WEIGHT = 0.4
AVAILABILITY_WEIGHT = 0.35
STYLE_WEIGHT = 0.25

# these numbers are the column positions in the CSV (found by checking the file)
SUBJECT_START = 5
SUBJECT_END = 42
AVAILABILITY_START = 42
AVAILABILITY_END = 47
STYLE_START = 47
STYLE_END = 52


def get_csv_file():
    # look for a csv file in the same folder as this program
    files_here = os.listdir(".")
    csv_files = []
    for f in files_here:
        if f.lower().endswith(".csv"):
            csv_files.append(f)

    if len(csv_files) == 0:
        print("No CSV file found. Put the CSV in the same folder as this program.")
        exit()
    elif len(csv_files) == 1:
        print("Using file:", csv_files[0])
        return csv_files[0]
    else:
        print("Found more than one CSV file:")
        for i in range(len(csv_files)):
            print(i + 1, "-", csv_files[i])
        choice = input("Which one should I use? Type the number: ")
        return csv_files[int(choice) - 1]


def read_students(filename):
    file = open(filename, newline="", encoding="utf-8-sig")
    reader = csv.reader(file)
    header = next(reader)  # first row is the column names

    students = []
    for row in reader:
        # skip empty rows
        if row.count("") == len(row):
            continue

        student = {}
        student["name"] = row[2].strip()
        if student["name"] == "":
            student["name"] = row[1].strip()
        student["year"] = row[4].strip()

        # get marks. Some subject names are repeated in the form
        # (like "Calculus" appearing twice) so we just take whichever
        # column actually has a number in it
        subjects = {}
        for col in range(SUBJECT_START, SUBJECT_END):
            subject_name = header[col].strip()
            mark = row[col].strip()
            if mark != "":
                subjects[subject_name] = float(mark)
            elif subject_name not in subjects:
                subjects[subject_name] = None
        student["subjects"] = subjects

        # get free days
        free_days = {}
        for col in range(AVAILABILITY_START, AVAILABILITY_END):
            day_name = header[col].strip()
            free_days[day_name] = row[col].strip()
        student["free_days"] = free_days

        # get study style answers
        style = {}
        for col in range(STYLE_START, STYLE_END):
            question = header[col].strip()
            style[question] = row[col].strip()
        student["style"] = style

        students.append(student)

    file.close()
    return students


def get_year_number(year_text):
    # turns "1st year Sem 1" or "3rd year" into just "1" or "3"
    # so students only get matched within their own year
    match = re.search(r"(\d+)(st|nd|rd|th)\s*year", year_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return year_text


def complement_score(s1, s2):
    # how much can these two help each other in subjects they BOTH take?
    shared_subjects = []
    for subject in s1["subjects"]:
        if s1["subjects"][subject] is not None and s2["subjects"].get(subject) is not None:
            shared_subjects.append(subject)

    if len(shared_subjects) == 0:
        return 0.0

    total_gap = 0
    for subject in shared_subjects:
        gap = abs(s1["subjects"][subject] - s2["subjects"][subject])
        total_gap += gap

    # marks are out of 5, biggest possible gap is 4
    return total_gap / (4 * len(shared_subjects))


def availability_score(s1, s2):
    days_checked = 0
    days_matching = 0
    for day in s1["free_days"]:
        slots1 = set(s1["free_days"][day].split(";"))
        slots2 = set(s2["free_days"][day].split(";"))
        slots1.discard("")
        slots2.discard("")

        if len(slots1) > 0 or len(slots2) > 0:
            days_checked += 1
            if len(slots1 & slots2) > 0:
                days_matching += 1

    if days_checked == 0:
        return 0.0
    return days_matching / days_checked


def style_score(s1, s2):
    same_answers = 0
    total_questions = len(s1["style"])
    for question in s1["style"]:
        answer1 = s1["style"][question]
        answer2 = s2["style"][question]
        if answer1 == answer2 or answer1 == "Either works" or answer2 == "Either works":
            same_answers += 1

    if total_questions == 0:
        return 0.0
    return same_answers / total_questions


def total_score(s1, s2):
    c = complement_score(s1, s2)
    a = availability_score(s1, s2)
    st = style_score(s1, s2)
    final = (c * COMPLEMENT_WEIGHT) + (a * AVAILABILITY_WEIGHT) + (st * STYLE_WEIGHT)
    return final, c, a, st


def make_pairs(students):
    # step 1: work out the score for every possible pair (but only
    # between students of the SAME year)
    all_possible_pairs = []
    for i in range(len(students)):
        for j in range(i + 1, len(students)):
            year_i = get_year_number(students[i]["year"])
            year_j = get_year_number(students[j]["year"])
            if year_i != year_j:
                continue  # don't match years together

            score, c, a, st = total_score(students[i], students[j])
            all_possible_pairs.append((score, i, j, c, a, st))

    # step 2: sort so the best pairs come first
    all_possible_pairs.sort(key=lambda x: x[0], reverse=True)

    # step 3: go down the list and lock in pairs, skipping anyone
    # who is already taken
    already_matched = []
    final_pairs = []
    for score, i, j, c, a, st in all_possible_pairs:
        if i in already_matched or j in already_matched:
            continue
        already_matched.append(i)
        already_matched.append(j)
        final_pairs.append((students[i], students[j], score, c, a, st))

    # anyone left over could not be matched
    leftover = []
    for i in range(len(students)):
        if i not in already_matched:
            leftover.append(students[i])

    return final_pairs, leftover


def main():
    filename = get_csv_file()
    students = read_students(filename)
    print("Total students:", len(students))

    pairs, leftover = make_pairs(students)

    print("")
    print("---- Matched Pairs ----")
    for pair in pairs:
        student1, student2, score, c, a, st = pair
        print(student1["name"], "+", student2["name"], "  (", student1["year"], ")")
        print("   overall score:", round(score, 2))
        print("   complement:", round(c, 2), " availability:", round(a, 2), " style:", round(st, 2))
        print("")

    if len(leftover) > 0:
        print("---- Could Not Be Matched ----")
        for student in leftover:
            print(student["name"], "(", student["year"], ")")


main()
