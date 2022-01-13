import functools
from mconfig import *


class Context:
    def __init__(self):
        self.reset()

    def reset(self):
        self.PhD_count = 0
        self.priorities = True
        self.priority_list = []
        self.min_remaining = True
        self.skills = True
global context
context = Context()


class SemesterHours:

    def __init__(self, semester = 'Y', hours = 0, preference = 'strong'):
        self.h = {sem:0 for sem in semesters}
        if semester == 'Y':
            self.h['F'] = hours/2
            self.h['S'] = hours/2
        elif preference == 'strong':
            self.h[semester] = hours
        else:
            self.h[semester] = int(0.75*hours)
            self.h[other_sem[semester]] = hours - self.h[semester] 
    
    def __add__(self, sh):
        new = SemesterHours()
        for sem in semesters:
            new.h[sem] = self.h[sem] + sh.h[sem]
        return new

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)
    
    def __getitem__(self, sem):
        return self.h[sem]

    def __setitem__(self, sem, v):
        self.h[sem] = v

    def __sub__(self, sh):
        new = SemesterHours()
        for sem in semesters:
            new.h[sem] = self.h[sem] - sh.h[sem]
        return new

    def __repr__(self):
        return ' '.join(key+str(int(self.h[key])) for key in self.h)

    def copy(self):
        new = SemesterHours()
        for sem in ['F', 'S']: new.h[sem] = self.h[sem]
        return new

class Assignment:

    def __init__(self, student, course, hours, comment = []):
        self.student = student
        self.course = course
        self.hours = hours
        self.course.assignment.append(self)
        self.student.assignment.append(self)
        self.comment = []
        self.make_comment(comment)

    def __del__(self):
        self.course.assignment.remove(self)
        self.student.assignment.remove(self)

    def add_hours(self):
        pass

    def add_comment(self, c):
        if not c in self.comment: self.comment.append(c)

    def make_comment(self):
        if self.student in self.course.pref:
            self.add_comment('C')
        if self.course in self.student.pref:
            self.add_comment('S')
        if self.student in self.course.good_experience:
            self.add_comment('G')
        if self.course.course_fields & self.student.course_fields:
            self.add_comment('F')
        for skill in important_skills:
            if self.course.skills[skill]>0.75 and self.student.skills[skill]==1:
                self.add_comment('I') 
        
class Market:

    def __init__(self, students, courses, what):
        self.courses = courses
        self.students = students
        self.what = what
        self.tightness = self.tightness_generic
        if what == 'everything':
            self.course_demand = lambda x: x.remaining
            self.student_supply = lambda x: x.remaining
        elif what in ['Y', 'F', 'S']:
            self.course_demand = functools.partial(Market.sem_demand, semester = what)
            self.student_supply = functools.partial(Market.sem_supply, semester = what)
        elif what in skill_description:
            self.course_demand = functools.partial(Market.skill_demand, skill = what)
            self.student_supply = functools.partial(Market.skill_supply, skill = what)
        elif what == 'grads':
            self.course_demand = Market.grads_demand
            self.student_supply = Market.grads_supply
        elif what in field_description.values():
            field = [f for f,d in field_description.items() if d == what][0]
            self.course_demand = functools.partial(Market.field_demand, field = field)
            self.student_supply = functools.partial(Market.field_supply, field = field)


    def sem_demand(course, semester):
        if course.semester == semester:
            return course.remaining
        return 0

    def sem_supply(student, semester):
        if semester == 'Y':
            return 2*min([student.remaining_sem[sem] for sem in semesters])
        else:
            return student.remaining_sem[semester]

    def skill_demand(course, skill):
        if course.skills[skill] >= 0.5:
            return course.skills[skill] * course.remaining
        return 0

    def skill_supply(student, skill):
        return student.skills[skill] * student.remaining
        
    def grads_demand(course):
        if course.grad_only:
            return course.remaining
        else: return 0

    def grads_supply(student):
        if student.type in grad_student_types:
            return student.remaining
        else: return 0

    def field_demand(course, field):
        if field in course.course_fields:
            return course.remaining
        else: return 0

    def field_supply(student, field):
        if field in student.course_fields:
            return student.remaining
        else: return 0

    def demand(self):
        return sum([self.course_demand(course) for course in self.courses])

    def supply(self):
        return sum([self.student_supply(student) for student in self.students])

    def tightness_generic(self):
        return self.demand() / (self.supply() + 0.0001)

    def first(self):
        return min([c for c in self.courses if self.course_demand(c) > 0], key = lambda c: c.satisfaction)
    

    


