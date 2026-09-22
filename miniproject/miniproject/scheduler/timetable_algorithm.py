import random
from collections import defaultdict

DAYS = 5
HOURS = 6
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
LAB_ROOMS = ["Lab A", "Lab B"]

# SUBJECT CLASS

class Subject:
    def __init__(self, name, teachers, hours, is_lab=False, preferred_lab=None):
        self.name = name
        self.teachers = teachers
        self.hours = hours
        self.is_lab = is_lab
        self.preferred_lab = preferred_lab

# TIMETABLE GENERATOR

class TimetableGenerator:
    def __init__(self, classes, subjects, reserved_slots, teacher_unavailability=None):
        self.classes = classes
        self.subjects = subjects
        self.reserved_slots = reserved_slots
        self.teacher_unavailability = teacher_unavailability or {}

        self.timetables = {
            c: [[None for _ in range(HOURS)] for _ in range(DAYS)]
            for c in classes
        }

        self.teacher_schedule = defaultdict(set)
        self.lab_schedule = {lab: set() for lab in LAB_ROOMS}

        # Track failures for conflict reporting
        self.failed_subjects = []

    def is_reserved(self, class_name, day, hour):
        if isinstance(self.reserved_slots, dict):
            return (day, hour) in self.reserved_slots.get(class_name, set())
        return (day, hour) in self.reserved_slots

    def teachers_free(self, teachers, day, hour):

        for t in teachers:
            if (day, hour) in self.teacher_schedule[t]:
                return False

        return True

    def teacher_available(self, teachers, day, hour):
        """Check if all teachers are available (not marked unavailable) at the given slot."""
        for t in teachers:
            unavail = self.teacher_unavailability.get(str(t), set())
            if (day, hour) in unavail:
                return False
        return True

    def no_consecutive(self, timetable, subject, day, hour):

        if hour > 0 and timetable[day][hour-1] == subject.name:
            return False

        if hour < HOURS-1 and timetable[day][hour+1] == subject.name:
            return False

        return True


    def max_per_day(self, timetable, subject, day, max_count=2):
        """Prevent more than max_count hours of the same subject per day."""
        count = sum(1 for h in range(HOURS) if timetable[day][h] == subject.name)
        return count < max_count

 
    #  THEORY SUBJECT
   
    def place_theory(self, class_name, subject):

        timetable = self.timetables[class_name]
        placed = 0
        attempts = 0

        while placed < subject.hours and attempts < 2000:
            day = random.randint(0, DAYS-1)
            hour = random.randint(0, HOURS-1)

            if self.is_reserved(class_name, day, hour):
                attempts += 1
                continue

            if timetable[day][hour] is not None:
                attempts += 1
                continue

            if not self.teachers_free(subject.teachers, day, hour):
                attempts += 1
                continue

            # Hard constraint: teacher availability
            if not self.teacher_available(subject.teachers, day, hour):
                attempts += 1
                continue

            if not self.no_consecutive(timetable, subject, day, hour):
                attempts += 1
                continue

            if not self.max_per_day(timetable, subject, day):
                attempts += 1
                continue

            timetable[day][hour] = subject.name

            for t in subject.teachers:
                self.teacher_schedule[t].add((day, hour))

            placed += 1

        return placed == subject.hours

    # PLACE LAB

    def place_lab(self, class_name, subject):

        timetable = self.timetables[class_name]

        #  3 hours constraints 
        if subject.hours != 3:
            return False

        # shuffling
        days = list(range(DAYS))
        random.shuffle(days)

        for day in days:

            # Only one lab per day 
            has_lab = False
            for h in range(HOURS):
                cell = timetable[day][h]
                if cell is not None:
                    
                    for c_subj in self.subjects[class_name]:
                        if c_subj.is_lab and c_subj.name == cell:
                            has_lab = True
                            break
                if has_lab:
                    break

            if has_lab:
                continue

            if self.try_lab_slot(class_name, subject, day, 0):
                return True

            if self.try_lab_slot(class_name, subject, day, 3):
                return True

        return False

# first half?second half
    def try_lab_slot(self, class_name, subject, day, start):

        timetable = self.timetables[class_name]

        if start not in (0, 3):
            return False

        end = start + 3
        if end > HOURS:
            return False


        chosen_lab = None
        if subject.preferred_lab:
            if subject.preferred_lab in self.lab_schedule and all(
                (day, h) not in self.lab_schedule[subject.preferred_lab] for h in range(start, end)
            ):
                chosen_lab = subject.preferred_lab
        else:
            for lab in LAB_ROOMS:
                if all((day, h) not in self.lab_schedule[lab] for h in range(start, end)):
                    chosen_lab = lab
                    break
        if chosen_lab is None:
            return False

        for h in range(start, end):

            if self.is_reserved(class_name, day, h):
                return False

            if timetable[day][h] is not None:
                return False

            if not self.teachers_free(subject.teachers, day, h):
                return False

            # Hard constraint: teacher availability
            if not self.teacher_available(subject.teachers, day, h):
                return False

        for h in range(start, end):

            timetable[day][h] = {"type": "Lab", "subject": subject.name, "lab": chosen_lab}

            for t in subject.teachers:
                self.teacher_schedule[t].add((day, h))

            self.lab_schedule[chosen_lab].add((day, h))

        return True

    def _analyze_conflicts(self):
        """Analyze why generation failed and produce a human-readable conflict report."""
        conflicts = []

        for class_name in self.classes:
            for subject in self.subjects.get(class_name, []):
                # Check if this subject was fully placed
                timetable = self.timetables[class_name]
                placed_count = 0
                for day in range(DAYS):
                    for hour in range(HOURS):
                        cell = timetable[day][hour]
                        if isinstance(cell, dict) and cell.get("type") == "Lab":
                            if cell.get("subject") == subject.name:
                                placed_count += 1
                        elif cell == subject.name:
                            placed_count += 1

                if placed_count < subject.hours:
                    # Find which teachers are blocked and where
                    blocked_slots = []
                    for t in subject.teachers:
                        unavail = self.teacher_unavailability.get(str(t), set())
                        for (d, h) in sorted(unavail):
                            blocked_slots.append({
                                "teacher_id": str(t),
                                "day": d,
                                "day_name": DAY_NAMES[d],
                                "period": h + 1,
                            })

                    conflicts.append({
                        "class": class_name,
                        "subject_id": subject.name,
                        "teachers": subject.teachers,
                        "required_hours": subject.hours,
                        "placed_hours": placed_count,
                        "blocked_slots": blocked_slots,
                    })

        return conflicts

    # GENERATE TIMETABLES

    def generate(self):

        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES):

            self.timetables = {
                c: [[None for _ in range(HOURS)] for _ in range(DAYS)]
                for c in self.classes
            }
            self.teacher_schedule = defaultdict(set)
            self.lab_schedule = {lab: set() for lab in LAB_ROOMS}

            all_success = True

            # Schedule labs 
            for c in self.classes:
                for subject in self.subjects.get(c, []):
                    if subject.is_lab:
                        success = self.place_lab(c, subject)
                        if not success:
                            print(f"[Attempt {attempt+1}] Failed scheduling lab {subject.name} for {c}")
                            all_success = False

            if not all_success:
                continue

            #  schedule theory 
            for c in self.classes:
                for subject in self.subjects.get(c, []):
                    if not subject.is_lab:
                        success = self.place_theory(c, subject)
                        if not success:
                            print(f"[Attempt {attempt+1}] Failed scheduling {subject.name} for {c}")
                            all_success = False

            if all_success:
                print(f"Timetable generated successfully on attempt {attempt+1}")
                return {"success": True, "timetables": self.timetables}

        # All retries exhausted — analyze and report conflicts
        conflicts = self._analyze_conflicts()
        if conflicts:
            print("Timetable generation failed due to teacher availability conflicts")
            return {"success": False, "conflicts": conflicts, "timetables": self.timetables}

        print("Returning best-effort timetable after all retries")
        return {"success": True, "timetables": self.timetables}


# PRINT TIMETABLE 
def print_tables(tables):

    for c, table in tables.items():

        print(f"\n\nTimetable for {c}")

        print("      H1   H2   H3   H4   H5   H6")

        for d in range(DAYS):

            row = DAY_NAMES[d] + "  "

            for h in range(HOURS):

                cell = table[d][h]
                if isinstance(cell, dict) and cell.get("type") == "Lab":
                    val = f"{cell.get('subject', 'Lab')}({cell.get('lab', '')})"
                else:
                    val = cell if cell else "--"

                row += f"{val:5}"

            print(row)


# MAIN (for CLI testing)
if __name__ == "__main__":

    classes = ["CSE-A"]
    subjects = {
        "CSE-A": [
            Subject("OS", ["DrRavi"], 4, False),
            Subject("CN", ["DrMeera"], 3, False),
            Subject("LabA", ["DrAjay", "DrAnil"], 3, True),
        ]
    }
    reserved = {"CSE-A": {(2, 2), (4, 4)}}

    generator = TimetableGenerator(classes, subjects, reserved)
    result = generator.generate()
    if result["success"]:
        print_tables(result["timetables"])
    else:
        print("Generation failed!")
        for c in result.get("conflicts", []):
            print(f"  Subject {c['subject_id']} in {c['class']}: placed {c['placed_hours']}/{c['required_hours']} hours")