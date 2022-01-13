#Classes devoted to handling people, mostly students (TAs)

from mconfig import params

from mclasses import *

class Person:
    def __init__(self, person_id, name):
        self.id=person_id
        self.name = name.encode('ascii', "ignore").decode()

    def __repr__(self):
        return self.name + '(jt:' + str(self.job_title)+')'

class Instructor(Person):
    def __init__(self, person_id, name, job_title):
        Person.__init__(self, person_id, name)
        self.job_title = job_title
        if self.job_title in job_title_translation:
            self.job = job_title_translation[self.job_title]
        else:
            self.job = 'other'
        self.bad_experience = []
        self.good_experience = {'grad':[],'undergrad':[], 'special':[]}


class Student(Person):

    def __init__(self, student_id, uoft_id, email, name, sex, t, non_econ, year, which, promised, max_hours, skills, comment, major, minor, course_fields):
        self.id = student_id
        self.uoft_id = uoft_id
        self.uoft = 0
        self.name = name
        self.email = email
        Person.__init__(self, student_id, name)
        self.sex = sex
        self.year = year
        self.non_econ = non_econ
        if t in student_types:
            self.type = t
        else:
            self.type = ''
            self.non_econ = True
        if self.non_econ and self.type in ['PhD', 'MA', '']:
            self.type += 'NonE'
        which['Y'] = which['F'] * which['S']
        self.which = which
        if which['F']==1 and which['S']==1:
            self.semester = 'Y' 
        elif which['F']==1 and which['S']==0:
            self.semester = 'F'
        elif which['F']==0 and which['S']==1:
            self.semester = 'S' 
        self.original_semester = self.semester
        self.semester_preference = 'strong' #This variable becomes weak in overrides if student prefers to split the allocation 25%-75% or something.
        #Other
        self.skills = skills
        self.comment = comment
        self.evaluations = []
        self.pref = []
        self.bad_pref = []
        self.evaluation = 3.001
        self.exclusions = set()
        self.assignment = []
        self.major = major
        self.minor = minor
        self.course_fields = course_fields
        self.add_field(major)
        self.add_field(minor)
        self.problems = []
        self.rejected = 0
        #The process of adding hours
        self.max_hours = max_hours
        self.max_allowed_hours = params.max_allowed_hours
        self.make_hours(self.max_hours)
        self.demanded = []
        if promised == None:
            promised = 0
        self.promised = promised
        self.funded = self.promised > 0
        self.field_quality = {field:0.8 for field in field_description}
        if self.type == 'PhD':
            self.MA_score = 1
        else:
            self.MA_score = 0.5
        self.compute_quality()
    
    def __repr__(self):
        star = ''
        main = self.type + ' ' + self.name + star +'('+str(int(self.remaining))+')'
        quality = '?'
        if self.evaluations != []:
            quality = 'E'+'{:1.1f}'.format(self.evaluation)
        elif self.type == 'MA' and self.MA_score != 0.5:
            quality = 'A'+'{:1.1f}'.format(5*self.MA_score)
        else:
            quality = '?'+'{:1.1f}'.format(5*self.quality)
        return main + ' ' + quality

    def add_field(self, field):
        if isinstance(field, int) and field>0:
            self.course_fields.add(field)

    def make_hours(self, max_hours = None):
        if max_hours == None:
            max_hours = self.max_hours
        #The Student.reduced property keeps track whether the current max_hours is temporarily reduced. 
        #In some parts of the algorithm (especially in the initial phases of the run), students are only allowed to use promised hours
        #so the algorithm reduces it to promised only (mprocess.Criterion.prepare_first_list()).    
        if max_hours < min(self.max_hours, self.max_allowed_hours):
            self.reduced = True
        else: self.reduced = False
        #Compute all hours available to the student
        self.hours = min(max_hours, self.max_hours, self.max_allowed_hours)
        self.hours_sem = SemesterHours(semester = self.semester, hours = self.hours, preference = self.semester_preference)
        #Compute remaining hours available to the student
        self.remaining = self.hours
        self.remaining_sem = SemesterHours(semester = self.semester, hours = self.hours, preference = self.semester_preference)
        for ass in self.assignment:
            self.remaining -= ass[1]
            if ass[0].semester == 'Y':
                for sem in semesters:
                    self.remaining_sem[sem] -= ass[1]/2
            else:
                self.remaining_sem.h[ass[0].semester] -= ass[1]
        if self.remaining <= 0:
            self.remaining = 0 
        #Set hours_margins and max_stretch variable
        if self.semester == 'Y':
            self.hours_margin = clone(params.hours_margin)
            if self.type == 'PhD' and self.year > 2:
                self.hours_margin = clone(params.old_hours_margin)
        else:
            self.hours_margin = clone(params.one_semester_margin) 
        self.max_stretch = min(params.max_stretch, max_hours + params.extra_strong_stretch - self.hours)
    
    def compute_quality(self):
        if self.evaluation != None:
            self.quality = self.evaluation 
        else:
            self.quality = quality_type[self.type]
        self.quality = self.quality/5
        self.quality_hierarchy = self.quality       
        if self.type in params.type_boost_hierarchy:
            self.quality_hierarchy += params.type_boost_hierarchy[self.type]

    def remove_from_blocks(self, course):
        if course.remaining <= 0:
            for l in [self.blocks_strong, self.blocks, self.demanded]:
                if course in l: l.remove(course)

    def assign_basic(self, course, hours, comment):
        if hours == 0:
            return
        self.remaining -= hours
        new_assignment = True
        for ass in self.assignment:
            if new_assignment and ass[0] == course:
                new_assignment = False
                old_ass = ass
        if new_assignment:
            self.assignment.append([course, hours, comment])
        else:
            old_ass[1] += hours
        self.remaining_sem = self.remaining_sem - SemesterHours(course.semester, hours)

    def assign(self,course, hours, comment, context = context):
        self.assign_basic(course, hours, comment)
        #Verify whether to drop from blocks
        
        #Check whether to add or drop from the priority list
        if self in context.priority_list:
            if self.remaining <= 0:
                context.priority_list.remove(self)
        elif context.priorities and self.remaining > 0:
            nsem = 0
            for sem in semesters: 
                if self.remaining_sem[sem]>0:
                    nsem += 1
            if len(self.assignment) + nsem >= priority_threshold:
                context.priority_list.append(self)
        self.remove_from_blocks(course)
    
    def compute_blocks(self, courses):
        self.first_best = []
        if len(self.pref) > 1 and self.pref[0].name == self.pref[1].name:
            self.first_best = [c for c in self.pref if c.name == self.pref[0].name]
        elif len(self.pref) > 0:
            self.first_best = {self.pref[0]}
        self.blocks_strong = [c for c in self.first_best if self in c.pref]
        self.blocks_strong.sort(key = lambda c:(c.pref.index(self), c.importance))
        self.blocks = [c for c in self.pref if self in c.pref]
        self.blocks.sort(key = lambda c:(c.pref.index(self), -c.importance))

    def underfunded(self):
        return min(self.promised, self.max_hours, self.max_allowed_hours) > self.total_assignment() + self.rejected

    def total_assignment(self):
        return sum([ass[1] for ass in self.assignment])

