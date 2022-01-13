

from mconfig import *
from mclasses import *
from mdata import MatchingData
from mCriterion import *



class Matching (MatchingData):

    def initialize_markets(self, active_courses):
        self.markets = []
        for what in ['everything', 'Y', 'F', 'S','grads'] + skill_description + rare_fields:
            self.markets.append(Market(self.students, active_courses, what))
        self.old_market = None

    def choose_market(self):
        market_list = [m for m in self.markets if m.demand() > 0]
        if market_list != []:
            self.market = max(market_list, key = lambda m: m.tightness())
            if self.old_market != self.market:
                self.log.add_line([''])
                self.log.add_line(['regular', 'Market for ' + self.market.what])
                self.old_market = self.market
        else:
            self.market = [m for m in self.markets if m.what == 'everything'][0]

    def find_competition(self, course, student):
        block_sequence = [student.blocks_strong, student.blocks, student.demanded, student.pref]
        finished, blocks = False, []
        for block in block_sequence:
            if not finished and course in block:
                finished = True
            if not finished:
                blocks += sorted(block, key = lambda c:c.satisfaction)
        competition = None
        if blocks != []:
            for comp in blocks:
                if competition == None:
                    sc = max(self.students, key = comp.satisfaction_increase)
                    if comp.satisfaction_increase(sc) > 0:
                        if sc == student or (not comp in sc.first_best and comp.satisfaction_increase(student, context = context) > params.block_threshold *comp.satisfaction_increase(sc, context = context)):
                            competition = comp
        return competition


    
    def find_match(self, course):
        #Main step of the algorithm - find a match for a given course
        #Returns h (float) 
        if course == None or course.remaining <= 0:
            return 0
        found = False
        while not found:
            student = max(self.students, key = course.satisfaction_increase)
            if course.satisfaction_increase(student) <= 0:
                student = None
                found = True
            else:
                if context.priority_list != []:
                    s_priority = max(context.priority_list, key = course.satisfaction_increase)
                    if course.satisfaction_increase(s_priority, context = context) >= params.priority_block_threshold * course.satisfaction_increase(student, context = context):
                        student = s_priority
                competition = self.find_competition(course, student)
                if competition != None:
                    h = competition.assign(student, self.log, context = context)
                else:
                    found = True
        if student != None:
            h = course.assign(student, self.log, context = context)
            self.log.make_last_line_bold()
        else: 
            h = 0
        return h


    #Main loop generating the assignment
    def generate_assignment(self):
        #Main loop of the algorithm
        active_courses = [course for course in self.courses]
        inactive_courses = []
        self.initialize_markets(active_courses) #dynamic list active_courses is fed into each market as a basis of demand and supply calculations
        end = Criterion(self, self.log, context)
        done = False
        while not done:
            self.choose_market()
            market_demand = self.market.demand()
            if market_demand > 0:
                course = self.market.first()
                h = self.find_match(course)
                if h <= 0:
                    active_courses.remove(course)
                    inactive_courses.append(course)
            else:
                done = end.check()
                active_courses += inactive_courses
                inactive_courses = []    
        #cycles = self.find_cycles(log)
        self.log.add_line(['-'*20])
        end.final_results()

    def find_cycles(self, log):
        #this method looks for possible trades. Such trades should not happen given the algorithm, but nevertheless, for some straneg reason, sometimes happen
        #it's not used for now
        cycle_length = 4
        def connected(p):
            outcome = []
            student = p[0]
            course = p[1]
            for ass in course.assignment:
                new_student = ass[0]
                if new_student != student:
                    outcome += [[new_student, a[0]] for a in new_student.assignment if a[0] != course]
            return outcome

        def process(cycle, log):
            hours = HIGH
            #check validity of a cycle
            valid = True
            F_cycle = 0
            S_cycle = 0

            for i in range(len(cycle)):
                p = cycle[i]
                student = p[0]
                course = p[1]
                if i < len(cycle)-1:
                    p_next = cycle[i+1]
                else: 
                    p_next = cycle[0]
                student_next = p_next[0]
                course_next = p_next[1]
                log.add_line([student_next.__repr__(), course.__repr__(), '--->', course_next.__repr__()])
                
                l = [a for a in course.assignment if a[0] == student_next]
                if len(l) == 0:
                    hours = 0
                else:
                    hours = min(hours, l[0][1])
                if course.semester == 'F':
                    F_cycle = 1
                if course.semester =='S':
                    S_cycle = 1
                if (not student in [a[0] for a in course.assignment]) or (not student_next in [a[0] for a in course.assignment]):
                    valid = False
            if not valid or hours<=0:
                log.add_line(['Already processed.'])
                log.add_line(['---------'])
                return 'y'
            if F_cycle*S_cycle == 1 and hours > 45:
                log.add_line(['Opposing semesters.'])
                log.add_line(['---------'])
                return 'y'
            log.add_line(['Hours traded: ', hours])
            answer = input('Accept y/n/e: ')
            if answer == 'y': 
                log.add_line(['Accepted.'])
                log.add_line(['---------'])
                for i in range(len(cycle)):
                    p = cycle[i]
                    student = p[0]
                    course = p[1]
                    if i < len(cycle)-1:
                        p_next = cycle[i+1]
                    else: 
                        p_next = cycle[0]
                    student_next = p_next[0]
                    course_next = p_next[1]
                    ass_course = [a for a in course.assignment if a[0] == student_next][0]
                    ass_student = [a for a in student_next.assignment if a[0] == course][0]
                    if ass_course[1]>hours:
                        ass_course[1] -= hours
                        ass_student[1] -= hours
                    else: 
                        course.assignment.remove(ass_course)
                        student_next.assignment.remove(ass_student)
                    ass_course = [a for a in course.assignment if a[0] == student][0]
                    ass_student = [a for a in student.assignment if a[0] == course][0]
                    ass_course[1] += hours
                    ass_student[1] += hours
                return 'y'
            log.add_line(['Rejected.'])
            log.add_line(['--------'])
            return answer

        cycles = []
        paths = []
        old_paths = []
        for student in self.students:
            old_paths += [[[student, ass[0]]] for ass in student.assignment]
        for level in range(cycle_length):
            new_paths = []
            for path in old_paths:
                for p in connected(path[-1]):
                    new_path = path+[p]
                    if new_path[-1][0] == new_path[0][0]:
                        cycle = [p for p in new_path][:-1]
                        outcome = process(cycle, log)
                        if outcome == 'e': return
                        if outcome == 'n':
                            cycle = cycle[::-1]
                            if process(cycle, log) == 'e': return
                    else:
                        new_paths.append(new_path)
            paths += old_paths
            old_paths = new_paths
