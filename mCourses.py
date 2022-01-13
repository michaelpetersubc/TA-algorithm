from mconfig import *
from mclasses import *

#Class devoted to handling courses
class Course:

    def __init__(self, course_id, name, u_number, g_number, subject, title, t, semester, instructor_list, hours, ug_ta_hours, allotment = None):
        self.id = course_id
        self.u_number = u_number
        self.g_number = g_number
        self.name = name
        self.title = title
        self.subject = subject
        self.instructor_list = instructor_list
        self.instructor = ''
        if isinstance(instructor_list, list):
            if len(instructor_list)>0:
                self.instructor = instructor_list[0].name
            if len(instructor_list)>1:
                self.instructor = instructor_list[0].name + ' and ' + instructor_list[1].name
        elif isinstance(instructor_list,str):
            self.instructor = instructor_list
            self.instructor_list = [self.instructor]
        self.type = t
        self.subtype = ''
        if self.type == 'g':
            if self.g_number>=2000 and self.g_number<3000:
                self.subtype = 'PhD1'
            elif self.g_number>=3000:
                self.subtype = 'PhD2'         
        if self.type != 'g':
            self.name_sort = '0' + self.name
        else:
            self.name_sort = self.name 
        if self.type =='u'  and self.name[0] in ['1','2','3','4']:
            self.year = int(self.name[0])
        elif self.type == 'ug' or self.subject == 'PPG':
            self.year = 5
        elif self.type == 'g' or self.name[0] == '5':
            self.year = 6
        self.semester = semester
        self.original_sem = semester
        self.make_hours(hours)
        self.ug_ta_hours = 0
        if isinstance(ug_ta_hours, int) or isinstance(ug_ta_hours, float): 
            self.ug_ta_hours = ug_ta_hours
        self.comment = ''
        self.exclusions = set()
        self.grad_only = True
        self.PhD_allotment(allotment)
         #preference
        self.pref = [None]*8
        self.bad_pref = [None]*2
        self.extended_pref = []
        self.good_experience = []
        self.utility_vec = {}
        self.demanded = []
        self.boost_type = {t:boost_type[t] for t in boost_type}
        self.assignment = []
        self.compute_importance()
        self.compute_satisfaction(context = context)
        #Special data downloaded from spreadsheet
        self.problems = []
        self.course_fields = set()

    def __repr__(self):
        h = '{:>6}'.format(str(self.hours))
        return '{:>7}'.format(self.name) + self.semester + ' {:>12.12}'.format(self.instructor)+'  ' + str(int(self.hours))+' ('+str(int(self.remaining))+')'

    def make_hours(self, hours):
        if isinstance(hours, SemesterHours):
            self.remaining_sem = hours.copy()
            self.hours_sem = hours.copy()
            total_hours = hours.h['F'] + hours.h['S']
            self.original_hours = total_hours
            self.hours = total_hours
            self.remaining = total_hours
        elif isinstance(hours, (int, float)):
            self.original_hours = hours
            self.hours = hours
            self.remaining = hours
            self.remaining_sem = SemesterHours(self.semester, hours)
            self.hours_sem = SemesterHours(self.semester, hours)
        
    def assign_skills(self, skills):
        self.skills = skills
        self.remaining_skills = {s: self.hours * self.skills[s] for s in skill_description}

    def assign_PhD_hours(self, hours_phd, hours_grad):
        self.hours_PhD = hours_phd 
        self.remaining_PhD = hours_phd
        self.hours_grad = hours_phd + hours_grad 
        self.remaining_grad = hours_phd + hours_grad
        if hours_phd + hours_grad < self.hours:
            self.grad_only = False

    def PhD_allotment(self, allotment = None, coeff=None):
        if allotment:
            self.assign_PhD_hours(allotment['phd'], allotment['grad'])
        else:
            def f(ht,coeff): 
                if coeff >= 1:
                    return ht
                h = [PhD_interval*int(ht*coeff/PhD_interval), min(ht,70*(1+int(ht*coeff/PhD_interval)))]
                p = (coeff*ht-h[0])/(h[1]-h[0])
                if PhD_random and random.random()>p:
                    return h[0]
                return h[1]
            if coeff == None:
                coeff = PhD_coeff[self.year]
            hours_phd = f(self.hours, coeff)
            hours_grad = self. hours - hours_phd
            self.assign_PhD_hours(hours_phd, hours_grad)

    def add_course_field(self, field):
        if field != None and field>0: self.course_fields.add(field)
            
    def add_exclusions(self, student):
        if not student in self.exclusions:
            self.exclusions.add(student)
        if not self in student.exclusions:
            student.exclusions.add(self)

    def compute_importance(self):
        self.importance = imp['years'] * self.year/7 + imp['hours'] * (self.hours+self.ug_ta_hours)/2000
        if self.year == 7:
            self.importance += 1
        if self.semester == 'Y':
            self.importance += Y_boost / alpha
        if self.g_number in important_courses:
            self.importance = 5

    def fulfillment(self):
        if self.remaining <= 0:
            fulfillment =  HIGH
        else: 
            if self.remaining_PhD > max_grad_margin_hours(self.hours, 'PhD'):
               factor = 1
            elif self.remaining_grad > max_grad_margin_hours(self.hours, 'grad'):
                factor = params.other_grad_hours
            else:
                factor = params.other_hours
            fulfillment = 1 - factor * self.remaining/self.hours
        return fulfillment
    
    def compute_satisfaction(self, context = context):
        self.satisfaction = - alpha *self.importance + self.fulfillment() / PhD_coeff[self.year]  

    def check_exclusions(self, students):
        for student in students:
            #available = student.which[self.semester] == 1
            #I took out not available and I am going to model it through hour_margin
            bad_experience = self.bad_pref
            for instructor in self.instructor_list:
                bad_experience += instructor.bad_experience
            too_young = False
            too_young = too_young or (student.type != 'PhD' and self.type == 'g')
            too_young = too_young or (student.year <= 1 and self.subtype == 'PhD1')
            too_young = too_young or (student.year <= 2 and self.subtype == 'PhD2')
            too_young = too_young and not student in self.pref
            student_unwillingness = self in student.bad_pref
            if student in bad_experience or too_young or student_unwillingness:
                self.add_exclusions(student)
                 
    def utility(self,student):
        u = 0
        if student in self.exclusions:
            u += -HIGH
            return u
        if student in self.pref:
            u += 1 + pref_coeff * (len(self.pref)+1-self.pref.index(student))/(len(self.pref)+1)
            return u
        if student in self.good_experience:
            u += boost['good experience']
        if student in self.extended_pref:
            boost_field = boost['field']
            if self.type == 'g':
                boost_field = boost['grad field']
            u += 0.5*boost_field *(1 + (len(self.extended_pref)+1-self.extended_pref.index(student))/(len(self.extended_pref)+1))
        if student in self.demanded:
            u += 0.5*boost['demanded'] *(1 + (len(student.pref)+1-student.pref.index(self))/(len(student.pref)+1))
        if student.which['F']*student.which['S'] == 0:
            u += boost['single semester']
        u += boost['quality'] * student.quality
        u += boost['type'] * self.boost_type[student.type]
        max_boost_type = max([self.boost_type[b] for b in boost_type])
        boosts_sum = sum([boost[b] for b in boost]) + max_boost_type
        if student.rejected >0:
            u += reject_penalty
        return u/boosts_sum

    def compute_utilities(self, students):
        for student in students:
            self.utility_vec[student.id] = self.utility(student)
        
    def available(self, student, context = context):
        #The goal of the reduced routine is the same as reduced part in Student.make_hours - check there
        #but, if the student is on the course preference list, we igonore the reduction - stupid kludge. 
        reduced = False 
        if student in self.pref and student.reduced:
            reduced = True
            student_total_hours = student.hours
            student.make_hours()
        if student.remaining <= 0 or self.remaining <=0:
            hours=0
        else:
            if student.type == 'PhD' and context.PhD_count == 0:
                PhD_cons = self.remaining_PhD  
                PhD_plus = self.remaining_PhD + max_grad_margin_hours(self.hours, 'PhD')
            else:
                PhD_cons, PhD_plus = HIGH, HIGH
            #Find student available hours. max_available is the maximum that the student can get convinced to. 
            if self.semester in ['F', 'S']:
                max_available = min(student.remaining + student.max_stretch, student.remaining_sem[self.semester]+student.hours_margin[self.semester])
                available = min(student.remaining, student.remaining_sem[self.semester])
            else: 
                max_available = min(student.remaining+student.max_stretch, 2*min([student.remaining_sem[sem]+student.hours_margin[sem] for sem in semesters]) )
                available = min(student.remaining, 2*min([student.remaining_sem[sem] for sem in semesters]))
            #Combine hours that are availbe from student wiht the course
            if self.remaining <= min(student.remaining, PhD_plus, max_available):
                hours = self.remaining
            elif student.remaining <= min(self.remaining, max_available, PhD_plus) and student.remaining>=0:
                hours = student.remaining
            else:
                hours = max(0,min(available, self.remaining, PhD_cons)) 
            if not student in [ass[0] for ass in self.assignment]:
                #Min size of the assignemtn that does not fill the course is min_remaining
                if context.min_remaining and self.remaining - hours < params.min_remaining and self.remaining - hours > 0:
                    hours = max(0,self.remaining - params.min_remaining)
                if student.remaining - hours < params.min_remaining and student.remaining - hours >0:
                    hours = max(0,student.remaining - params.min_remaining)
                #Check the priorities
                if hours > 0 and context.priorities and student in context.priority_list and not self in student.pref:
                    fills_something = hours >= student.remaining
                    for sem in semesters:
                        if student.remaining_sem[sem] > 0 and self.semester in [sem,'Y'] and hours >= student.remaining_sem[sem]:
                            fills_something = True
                    if not fills_something: 
                        hours = 0
        #This part closes and reverses the reduce rouutine from above 
        if student in self.pref and reduced:
            student.make_hours(student_total_hours) 
        return hours

    def skills_match(self, student, context = context):
        if not context.skills or self.remaining <=0 or student in self.pref or student in self.good_experience:
            return 1
        if self in student.pref and student.type == 'PhD' and student.year >= 2:
            return 1
        need = {s:self.remaining_skills[s]/self.remaining for s in skill_description}
        d = 1
        l = len(skill_description)
        for s in skill_description:
            if need[s] > student.skills[s]:
                d -= s_plus * skill_relevance[s] * (need[s] - student.skills[s])/l
            else: 
                d -= s_minus * skill_relevance[s] * (student.skills[s] - need[s])/l
        return max(d,0.1)

    def satisfaction_increase(self, student, context = context):
        coeff = 1 + max(len(student.assignment)-2,0) * many_courses_boost
        aval = self.available(student, context = context)
        util = self.utility_vec[student.id]
        match = self.skills_match(student, context = context)
        if self.remaining_PhD < max_grad_margin_hours(self.hours, 'PhD'):
            hours_available = params.max_hours_available
        else:
            hours_available = min(self.remaining_PhD, params.max_hours_available)
        return min(hours_available ,coeff * aval) * util * match

    def assign_basic(self, student, hours, comment):
        self.remaining -= hours
        self.remaining_sem = SemesterHours(self.semester, self.remaining)
        for s in skill_description:
            if student in self.pref:
                self.remaining_skills[s] -= hours
            else:
                self.remaining_skills[s] -= hours * student.skills[s]
            self.remaining_skills[s] = max(0, min(self.remaining, self.remaining_skills[s]))
        if student.type == 'PhD':
            self.remaining_PhD -= hours
        if student.type in grad_student_types:
            self.remaining_grad -= hours
        new_assignment = True
        for ass in self.assignment:
            if new_assignment and ass[0] == student:
                ass[2] = ass[2] + [c for c in comment if not c in ass[2]]
                new_assignment = False
                ass[1] += hours
        if new_assignment:
            self.assignment.append([student, hours, comment])

    def assign(self, student, log, context = context):
        h = self.available(student, context = context)
        if h<=0:
            return 0
        #Assign
        prev_demand = {skill:self.remaining_skills[skill] for skill in skill_description} #skill coverage before student is assigned
        comment = self.ass_comment(student)
        self.assign_basic(student, h, comment)
        student.assign(self, h, comment, context = context)
        self.compute_satisfaction(context = context)
        log.add_line([self.__repr__(), '{0} ({1}) '.format(student.__repr__(),str(int(student.remaining)))+''.join(comment), str(int(h))])
        return h

    def mismatched(self, student):
        return not self in student.pref and not student in self.pref and not student in self.good_experience

    def ass_comment(self, student):
        #Create comments
        comment = []
        if student in self.pref:
            comment.append('C')
        if self in student.pref:
            comment.append('S')
        if student in self.good_experience:
            comment.append('G')
        if self.course_fields & student.course_fields:
            comment.append('F')
        for skill in important_skills:
            if self.skills[skill]>0.75 and student.skills[skill]==1 and not 'I' in comment:
                comment.append('I')
        return comment



