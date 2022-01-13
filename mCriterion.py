import xlrd, xlwt
import random
from mconfig import *

from mclasses import *
from termcolor import colored
#from mreports import Report
#from mreports import merge
#import datetime, os


class Goal:
    def __init__(self, name, is_satisfied, initiate_tool, tools):
        self.name = name
        self.is_satisfied = is_satisfied
        self.initiate_tool = initiate_tool
        self.tools = tools
    
    def use_tool(self):
        if self.tools == []:
            return False
        else: 
            self.tools[0]()
            self.tools.pop(0)
            return True

    def insert_tool(self, tool):
        self.tools.insert(0, tool)

    def initiate(self):
        if self.initiate_tool != None:
            self.initiate_tool()
            return True
        else: return False

class Criterion:

    def __init__(self, matching, log, context):
        self.students = matching.students
        self.courses = matching.courses
        self.instructors = matching.instructors
        self.student_map = matching.student_map
        self.log = log
        self.context = context
        context.reset()
        funded = Goal('All promised hours are delivered', self.funded, self.prepare_first_list, [self.raise_PhD_constraint, self.override_hours_margin, self.cancel_priority_list])
        filled_grad_only = Goal('All grad_only courses are filled', self.filled_grad_only, self.maximize_hours, [self.cancel_priority_list, self.ignore_skills])
        filled = Goal('All courses are filled', self.filled, self.maximize_hours, []);        
        self.goals = [funded, filled_grad_only, filled]
        self.outcomes = []
        if self.goals != []: self.goals[0].initiate()   

    def check(self):
        goal = self.goals[0]
        if goal.is_satisfied():
            self.outcomes.append([goal.name,True])
            self.goals.pop(0)
            if self.goals != []: self.goals[0].initiate()   
        elif not goal.use_tool():
            self.outcomes.append([goal.name,False])
            self.goals.pop(0)
            if self.goals != []: self.goals[0].initiate() 
        if self.goals == []:
            return True
        return False

    def funded(self):
        return len([s for s in self.students if s.underfunded()]) == 0

    def override_hours_margin(self):
        message = 'Lifting hour imbalance constraint  '
        self.log.add_line(['bold',message, '.'*20])
        for student in self.students:
            if student.underfunded():
                student.hours_margin = {sem:max(student.hours_margin['F'], student.hours_margin['S'], student.max_allowed_hours) for sem in semesters}

    def filled(self):
        return len([c for c in self.courses if c.remaining > 0]) == 0

    def filled_grad_only(self):
        return len([c for c in self.courses if c.remaining > 0 and c.grad_only]) == 0              

    def final_results(self):
        for o in self.outcomes:
            self.log.add_line(['Goal: ', o[0], str(o[1])])
    
    def __repr__(self):
        trans = {True:' achieved!', False:colored(' failed. ):', 'red')}
        return '\n'.join(['Goal: ' + colored(o[0],'green') + trans[o[1]] for o in self.outcomes])

    def prepare_first_list(self):
        message = 'Preparing initial list  '
        self.log.add_line(['bold',message, '.'*20])
        students, courses = self.students, self.courses
        demand = sum([c.remaining_sem for c in courses])
        self.log.add_line(['Demand:', demand.__repr__()])
        #Find promised supply
        supply = SemesterHours()
        for student in students:
            student.make_hours(student.promised)
            supply += student.remaining_sem
        self.log.add_line(['Supply (promised):', supply.__repr__()])
        #prepare hierarchy of students
        hierarchy = sorted(students, key = lambda s:s.quality_hierarchy, reverse = True)
        def over_threshold(demand, supply):
            return min([min(params.demand_threshold_relative*demand[sem], demand[sem]-params.demand_threshold_absolute) - supply[sem] for sem in semesters])<0
        stop = over_threshold(demand, supply)
        i = 0
        while not stop:
            student = hierarchy[i]
            supply -= student.remaining_sem
            student.make_hours()
            supply += student.remaining_sem
            i += 1
            stop = i>=len(hierarchy) or over_threshold(demand, supply)
        self.log.add_line(['Supply (prepared):',supply.__repr__()])
        
    def raise_PhD_constraint(self, increase = 0.05):
        old_count, new_count = self.context.PhD_count, self.context.PhD_count + increase
        total = 0
        for course in self.courses: 
            old_level = 35*int(course.hours_PhD*(1+old_count)/35)
            new_level = 35*int(course.hours_PhD*(1+new_count)/35)
            course.remaining_PhD += new_level - old_level
            total += new_level - old_level 
            course.remaining_PhD = min(course.remaining, course.remaining_PhD)
        self.context.PhD_count += increase
        self.complete_assignments()
        message = 'Lifiting PhD constraint by ' + str(int(total))+'h'
        self.log.add_line(['bold',message, '.'*20])
        
        if self.context.PhD_count < 1:
            self.goals[0].insert_tool(self.raise_PhD_constraint)
    
    def complete_assignments(self):
        for course in self.courses:
            for ass in course.assignment:
                h = course.assign(ass[0], self.log, context = context)     

    def maximize_hours(self):
        message = 'Increasing hours to maximum requested ...'
        self.log.add_line(['bold',message, '.'*20])
        self.raise_PhD_constraint(increase = 2)
        for student in self.students:
            student.make_hours()
        self.complete_assignments()
        self.context.priorities = True
        self.context.priority_list = []

    def cancel_priority_list(self):
        message = 'Ignoring student priority list  '
        self.log.add_line(['bold',message, '.'*20])
        self.context.priorities = False
    
    def ignore_skills(self):
        message = 'Ignoring skill requirements  '
        self.log.add_line(['bold',message, '.'*20])
        self.context.skills = False
