
'''
With an exception of merge,
All free stadning methods in this module are imported as class methods into class Matching in mprocess
Their purpose is to generate reports from an assignment

Class Report outputs the reports either on screen, or into an Excell spreadsheet. 
Method merge serves to merge multiple reports into a single one (it is used in comparing across years)
'''
from mconfig import *

import xlrd, xlwt
import datetime, random
from mclasses import *
from termcolor import colored
import os

#from mdata import script_directory, past_data_directory, output_directory

def pecking_order_report(self):
    pecking_order = sorted(self.courses, key = lambda c:c.satisfaction)
    pecking_report = [[c.name, c.title, c.instructor, c.hours, c.year, c.semester] for c in pecking_order]
    pecking_report.insert(0, ['name', 'title', 'instructor', 'hours', 'year', 'semester'])
    return pecking_report


def remaining_report(self):
    report = []
    report.append(['bold', 'Course demand', 'regular', 'initial','F', 'S', 'remaining', 'F', 'S'])
    demand = sum([c.hours_sem for c in self.courses])
    report.append(['all courses', ''] + [int(demand[sem]) for sem in semesters] + ['', 0, 0])
    categories = {}
    categories['all students'] = self.students
    report.append([''])
    report.append(['bold', 'Student supply', 'regular', 'initial','F', 'S', 'remaining', 'all sems', 'F', 'S'])
    for cat in categories:
        if categories[cat] != []:
            supply = sum([s.hours_sem for s in categories[cat]])
            remaining = sum([s.remaining for s in categories[cat]])
            remaining_sem = sum([s.remaining_sem for s in categories[cat]])
            line = [cat, ''] + [int(supply[sem]) for sem in semesters]+['', int(remaining)] + [int(remaining_sem[sem]) for sem in semesters]
            report.append(line)
    report.append([''])
    report.append(['bold', 'Student list'])
    report.append(['', 'promised rem', 'semester', 'all remaining', 'remaining F', 'remaining S'] + skill_description + ['preferences'])
    student_list = sorted(self.students, key = lambda s:s.remaining, reverse = True)
    for s in student_list:
        old_total = sum([ass[1] for ass in s.old_ass])
        line = [s.type+' '+s.name, int(max(s.promised-old_total,0)), s.semester] + [int(s.remaining)] + [int(s.remaining_sem[sem]) for sem in semesters]
        line += [s.skills[skill] for skill in skill_description]
        pref_list = sorted([c.u_number for c in s.pref if c.u_number != None])
        line += [','.join([str(u) for u in pref_list])]
        line += ['red'] + s.problems
        report.append(line)
    return report
    
def course_ass_report(self, which_semesters = ['F', 'S', 'Y']):
    report = []
    courses = [c for c in self.courses if c.semester in which_semesters]
    for course in courses:
        #Process problems
        if course.remaining>0:
            course.problems.append('Unfilled: '+str(int(course.remaining))+'!')
        TA_on_pref_list = False
        min_ass = 280
        for ass in course.assignment:
            if ass[0] in course.pref + course.good_experience:
                TA_on_pref_list = True
            min_ass = min(ass[1], min_ass)
        if course.pref != [] and not TA_on_pref_list:
            course.problems.append('No TA from the pref list nor good experience.')
        if min_ass < params.min_remaining:
            course.problems.append('Smallest assignment is ' + str(int(min_ass))+'.')
        small_assignments = [ass for ass in course.assignment if ass[1]<35]
        if len(small_assignments)>1:
            course.problems.append('There are {0} small assignments.'.format(len(small_assignments)))
        for skill in skill_description:
            satisfaction = 0
            for ass in course.assignment:
                if ass[0] in course.pref:
                    satisfaction += ass[1]
                else:
                    satisfaction += ass[0].skills[skill] * ass[1]
            satisfaction = (satisfaction+1)  / (course.hours*course.skills[skill]+1)
            if satisfaction < problematic_skill_satisfaction[skill]:
                course.problems.append('Skill {0} coverage at {1}%'.format(skill, int(100*satisfaction)))
        #First line - course name and hour composition
        if course.problems == []: 
            style = 'bold'
        else:
            style = 'red'
        hours = str(course.hours+course.ug_ta_hours)
        if course.ug_ta_hours > 0:
            hours = hours + ' ('+str(course.hours)+' reg.)'
        line = [style, course.name+course.semester, course.instructor, course.title, hours] + ['regular'] + ['']*3
        f = {t:0 for t in student_types}
        for ass in course.assignment:
            f[ass[0].type] += ass[1]
        for t in student_types:
            if t == "PhD":
                line.append(t+': {0}% ({1})'.format(int(100*f[t]/course.hours),int(100*course.hours_PhD/course.hours)))
            else:
                line.append(t+': {0}%'.format(int(100*f[t]/course.hours)))
        report.append(line)
        #Second line - assignments
        line = [str(course.id), 'Assignment']
        for ass in course.assignment:
            if ass[2] == []:
                line.append('pink')
            elif 'C' in ass[2] or 'G' in ass[2]:
                line.append('green')
            elif 'S' in ass[2]:
                line.append('blue')
            line.append(ass[0].__repr__()+' ('+str(ass[1])+')'+''.join(ass[2]))
        report.append(line)
        #The rest
        AvAss = course.hours/(len(course.assignment)+0.0001)
        if course.semester == 'Y':
            AvAss = AvAss/2
        color = 'regular'
        if AvAss <60 and len(course.assignment)>1:
            color = 'red'
        report.append([color, 'AvAss: {0}'.format(int(AvAss)), 'regular', 'Preferences']+[s.__repr__() for s in course.pref])
        demanded = []
        for student in course.demanded:
            student_assignments = [ass for ass in student.assignment if ass[0].semester in which_semesters]
            if student_assignments != [] or student.remaining>0:
                demanded.append(student.__repr__())
        report.append(['small', '', 'Demanded']+[s.__repr__() for s in demanded])
        '''
        #Bad experience or exclusions
        bad_experience = []
        for instructor in course.instructor_list:
            bad_experience += instructor.bad_experience
        #report.append(['small', '', 'Exclusions']+[s.type+s.name for s in course.bad_pref] + [s.name for s in bad_experience])
        '''
        report.append(['small', '', 'Comment', course.comment])
        if course.problems != []:
            report.append(['small', '', 'Problems','red'] + course.problems)
        report.append([''])
    return report

def student_ass_report(self, which_semesters = ['F', 'S', 'Y']):
    report = []
    for student in self.students:
        student_assignments = [ass for ass in student.assignment if ass[0].semester in which_semesters]
        if student_assignments != [] or student.remaining>0:
            #Process problems
            if student.underfunded():
                student.problems.append('Underfunded!')
            unbalance = max([-student.remaining_sem[sem] for sem in semesters])
            if unbalance > 35:
                student.problems.append('Unbalanced assignment '+ str(int(unbalance))+'h')
            if student.remaining < 0:
                student.problems.append('Stretched assignment '+ str(-int(student.remaining)) +'h')
            if len(student.assignment) > 5:
                student.problems.append('Many assignments '+ str(len(student.assignment)))
            #the rest
            if student.problems == []: 
                style = 'bold'
            else:
                style = 'red'
            
            line = [style, student.type+student.name, student.semester, 'bold', student.hours, 'regular', student.promised] + ['']*3
            line += ['regular','Remaining', student.remaining] + [str(int(student.remaining_sem[sem]))+sem for sem in ['F', 'S']]
            if student.evaluations != []:
                line += ['regular','Overall', student.evaluation] 
            report.append(line)
            line = [str(student.id), 'Assignment']
            for ass in student_assignments:
                if ass[2] == []:
                    line.append('pink')
                elif 'C' in ass[2] or 'G' in ass[2]:
                    line.append('green')
                elif 'S' in ass[2]:
                    line.append('blue')
                line.append(ass[0].name+ass[0].semester+' '+ass[0].instructor+' '+' ('+str(ass[1])+')'+''.join(ass[2]))

            report.append(line)
            report.append(['small', '', 'Preferences']+[c.name for c in student.pref]) 
            report.append(['small', '', 'Demanded']+[c.name for c in student.demanded])
            report.append(['small', '', 'Comment', student.comment])
            if student.problems != []:
                report.append(['small', '', 'Problems', 'red'] + student.problems)
            report.append([''])
    return report
        
def matching_report(self, report = None):
    #Preparations
    if self.name != None:
        output = self.name
    else:
        output = 'Assignment'+self.year_code+self.session
    self.log.add_line(['Saving for output ',output])
    if report == None:
        report = Report(name = output)
    
    #Do all the work
    report.save_matching(self)
    report.add_sheet(self.course_ass_report(), 'Courses'+self.session_code)
    report.add_sheet(self.student_ass_report(), 'Students'+self.session_code)
    return report

def student_report(self):
    report = [['Name', 'program', 'year', 'email', 'requested h', 'semester', 'fields', 'promised h', 'remaining', 'PhD h', 'comment', 'Problems']]
    lmain = len(report[0])-1
    tr, tp = 0, 0
    count = {t:0 for t in student_types}
    student_field = {field:[] for field in field_description}
    for student in self.students:
        count[student.type] += 1
        h = student.max_hours
        tr += h            
        PhD_h = 0
        if student.type == 'PhD':
            PhD_h = h
            tp += PhD_h
        fields = ','.join([str(f) for f in student.course_fields])
        for field in student.course_fields:
            student_field[field].append(student)
        line = [student.name, student.type, str(student.year), student.email, str(h), student.semester, fields, str(student.promised), student.remaining, PhD_h, student.comment]
        problems = ['red'] + student.problems
        semester_mismatch = False
        for course in student.pref:
            for semester in semesters:
                if course.hours_sem[semester]>0 and student.hours_sem[semester]==0:
                    semester_mismatch = True
        if semester_mismatch:
            problems.append('Semester requested mismatched with preferenced courses.')
        report.append(line + problems)
        line = ['']*lmain
        for c in student.pref:
            line.append(c.__repr__())
        report.append(line)
    for field in field_description:
        report.insert(0,[field_description[field]]+[s.__repr__() for s in student_field[field]])    
    report.insert (0, ['Totals', '', '', str(tr), '', str(tp), ''])
    report.insert(0, [str(count[t])+' '+t+'s' for t in student_types])
    return report

def student_summary(self):
    report = []
    report.append(['Type', 'Name', 'Year', 'Semester', 'Requested h', 'Promised h', 'Filled h', 'Remaining',  'Filled F', 'Remaining F'])
    for s in self.students:
        filled, filledF = 0,0
        for ass in s.assignment:
            filled += ass[1]
            if ass[0].semester == 'F':
                filledF += ass[1]
            elif ass[0].semester == 'Y':
                filledF += 0.5 * ass[1]
        report.append([s.type, s.name, s.year, s.semester, str(int(s.max_hours)), str(int(s.promised)), str(int(filled)), str(int(s.remaining)), str(int(filledF)), str(int(s.remaining_sem['F']))])
    return report

def diagnostics(self, campus = '15'):

    #prepare campus data
    if campus == '15':
        instructors, students, courses, name = self.instructors, self.students, self.courses, self.name
        campus_set = {'1', '5'}
    elif campus in [1,5]:
        campus_set = {str(campus)}
        instructors, students, name = self.instructors, self.students, self.name+str(campus_map[campus])
        courses = [c for c in self.courses if c.name[-1] == str(campus)]
    for student in students:
        student.c_assignment = [ass for ass in student.assignment if ass[0].name[-1] in campus_set]

    #Name

    lc = len(courses)
    report = [['MATCHING NAME', name]]
    
    #Course preferences
    report.append(['',''])
    report.append(['COURSE PREFERENCES ' ,''])
    total_TA = 0
    for course in courses: 
        for ass in course.assignment:
            total_TA += 1       
    report.append(['Average TA per course ', '{0:.3}'.format(total_TA/lc)])
    th, ph, eh, fh, tc, pc, ec, anybody_t, anybody_tpg, n_c = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 
    for course in courses:
        n_c += 1
        anybody_p = False
        anybody_g = False
        for ass in course.assignment:
            th += ass[1]
            tc += 1
            if ass[0] in course.pref:
                anybody_p = True
                ph += ass[1]
                pc += 1
            elif ass[0] in course.good_experience:
                anybody_g = True
                eh += ass[1]
                ec += 1 
            elif ass[0] in course.extended_pref:
                fh += ass[1]
        if anybody_p:
            anybody_t += 1
        if anybody_p or anybody_g:
            anybody_tpg += 1
    report.append(['Percentage of TA hours on course preferences: ', '{0:.0f}%'.format(100*ph/th)])
    report.append(['Percentage of TA hours on course preference + good experience: ', '{0:.0f}%'.format(100*(eh+ph)/th)])
    report.append(['Percentage of TA hours on course preference + good experience + field: ', '{0:.0f}%'.format(100*(fh+eh+ph)/th)])
    report.append(['Percentage of TAs on courses preference lists: ', '{0:.0f}%'.format(100*pc/tc)])
    report.append(['Percentage of TAs on courses preference + good experience: ', '{0:.0f}%'.format(100*(pc+ec)/tc)])
    report.append(['Percentage of courses with a TA from pref list: ', '{0:.0f}%'.format(100*(anybody_t)/n_c)])
    report.append(['Percentage of courses with a TA from pref list or good experience: ', '{0:.0f}%'.format(100*(anybody_tpg)/n_c)])
    cpref_length = {}
    report.append(['Average number of TAs per course by year: ',''])
    nta_year, tc_year = {year:0 for year in course_years}, {year:0 for year in course_years}
    for course in courses:
        tc_year[course.year] += 1
        nta_year[course.year] += len(course.assignment)
    for year in course_years: 
        report.append(['Average number of TAs per course in year {}'.format(year), '{0:.2f}'.format(nta_year[year]/(tc_year[year]+0.0001))])
    
    for course in courses:
        l = len(course.pref)
        if l in cpref_length:
            cpref_length[l] += 1
        else: 
            cpref_length[l] = 1
    
    #Student preferences
    report.append(['',''])
    report.append(['STUDENT PREFERENCES ',''])
    t_c = 0
    course_max = 0
    students_max = []
    stretched_hours = 0
    n_s = 0
    for student in students:
        n_c=len(student.c_assignment)
        if n_c > course_max:
            students_max = [student]
            course_max = n_c
        elif n_c == course_max:
            students_max.append(student)
        t_c += n_c
        if n_c>0:
            n_s += 1
        h = sum([ass[1] for ass in student.c_assignment])
        stretched_hours += max(h - min(student.max_hours, student.max_allowed_hours), 0)
    report.append(['Average courses per TA: ','{0:.3}'.format(t_c/n_s)])
    report.append(['Maximum number of courses: ', str(course_max)])
    report.append(['Students max:  ', str(students_max)])
    report.append(['Total stretched hours ', str(stretched_hours)])
    th, ph, nc, tc = 0, 0, 0, 0
    for student in students:
        for ass in student.c_assignment:
            th += ass[1]
            tc += 1
            if ass[0] in student.pref:
                ph += ass[1]
                nc += 1
    report.append(['Percentage of TA hours on the student preference lists: ', '{0:.0f}%'.format(100*ph/th)])
    report.append(['Percentage of courses on the student preference lists: ', '{0:.0f}%'.format(100*nc/tc)])
    #Testing student preferences
    th, ph = {t:0 for t in student_types}, {t:0 for t in student_types}
    for student in students:
        for ass in student.c_assignment:
            th[student.type] += ass[1]
            if ass[0] in student.pref:
                ph[student.type] += ass[1]
    report.append(['By student type:', ''])
    for t in student_types:
        report.append(['Percentage of TA hours on {}s preference lists: '.format(t), '{0:.0f}%'.format(100*ph[t]/(th[t]+0.00001))])

    #Blocks
    report.append(['',''])
    report.append(['BLOCKS ',''])
    report.append(['Perfect match - course and student on top',''])
    report.append(['Block - course and student on pref list (strong, if course on top for student)',''])
    perfect_match, perfect_ass = 0,0
    for student in students:
        for course in student.first_best:
            if course.pref != [] and student == course.pref[0]:
                perfect_match += 1
                for ass in student.c_assignment:
                    if course == ass[0]:
                        perfect_ass += 1
    report.append(["Perfect matches assigned: ", str(perfect_ass)+'/'+str(perfect_match)])
    total_strong_blocks, blocks_ass = 0,0
    for student in students:
        student.compute_blocks(courses)
        total_strong_blocks += len(student.blocks_strong)
        for ass in student.c_assignment:
            if ass[0] in student.blocks_strong:
                blocks_ass += 1
    report.append(["Strong blocks assigned: ", str(blocks_ass)+'/'+str(total_strong_blocks)])
    total_blocks, blocks_ass = 0,0
    for student in students:
        total_blocks += len(student.blocks)
        for ass in student.c_assignment:
            if ass[0] in student.blocks:
                blocks_ass += 1
    report.append(["Blocks assigned: ", str(blocks_ass)+'/'+str(total_blocks)])
    #Mismatched hours
    report.append(['',''])
    report.append(['MISMATCHED HOURS ',''])
    report.append(['Mismatch means that student nor course on preference lists, and no good history',''])
    total_year = {y:0 for y in course_years}
    mismatched_year = {y:0 for y in course_years}
    for course in courses:
        for ass in course.assignment:
            total_year[course.year] += ass[1]
            if course.mismatched(ass[0]):
                mismatched_year[course.year] += ass[1] 
    for y in course_years:
        report.append(['Percentage of mismatched TA hours in year {0}: '.format(y), '{0:.0f}%'.format(100*mismatched_year[y]/(total_year[y]+0.0001))])
    #Skill satisfaction
    report.append(['',''])
    report.append(['DEMAND AND SUPPLY OF SKILLS',''])
    cskills = {s:0 for s in skill_description}
    satisfied_skills = {s:0 for s in skill_description}
    satisfied_skills_nopref = {s:0 for s in skill_description}
    sskills = {s:0 for s in skill_description}
    total_students = 0
    for course in courses:
        for s in skill_description:
            cskills[s] += course.hours * course.skills[s]
            if s==6 and course.skills[s]>0:
                k=3
            skill_satisfaction = 0
            skill_nopref =0
            for ass in course.assignment:
                if ass[0] in course.pref+course.good_experience:
                    skill_satisfaction += ass[1]
                else:
                    skill_satisfaction += ass[0].skills[s] * ass[1]
                    skill_nopref += ass[0].skills[s] * ass[1]
            satisfied_skills[s] += min(course.hours * course.skills[s],  skill_satisfaction)
            satisfied_skills_nopref[s] += min(course.hours * course.skills[s],  skill_nopref)
    for student in students:
        for s in skill_description:
            sskills[s] += student.hours * student.skills[s]
        total_students += student.hours
    report.append(['Total student hours: ', ' {:.0f}'.format(total_students)])
    report.append(['{:>10.10s}'.format('skill') + '{:>8.8s}'.format('demand') + '{:>8.8s}'.format('supply'),''])
    report.append(['Percentage of skill+pref (percentage of skill)',''])
    for s in skill_description:
        sat = ' {:>3.0f}%'.format(100 *(satisfied_skills[s]+0.0001)/(cskills[s]+0.0001))
        sat_nopref = ' ({:>3.0f}%)'.format(100 *(satisfied_skills_nopref[s]+0.0001)/(cskills[s]+0.0001))
        report.append(['{:>10.10s}'.format(s) + '{:>8.0f}'.format(cskills[s]) + '{:>10.0f}'.format(sskills[s]), sat+sat_nopref])
    #Phds per year
    report.append(['',''])
    report.append(['PHD ALLOCATION ',''])   
    t_y = {y:0 for y in course_years}
    p_y = {y:0 for y in course_years}
    for course in courses:
        cyear = course.year
        for ass in course.assignment:
            t_y[cyear] += ass[1]
            if ass[0].type == 'PhD':
                p_y[cyear] += ass[1]
    for cyear in course_years:
        report.append(['PhD precentage in courses year {0}:'.format(str(cyear)),'{0:.0f}%'.format(100*p_y[cyear]/(t_y[cyear]+0.00001))])
    #ABASIC STATISTICS
    report.append(['',''])
    report.append(['BASIC STATISTICS ',''])
    report.append(['Total students: ',str(len(students))])
    supply_hours = sum([s.hours for s in students])
    report.append(['Total supply: ',str(int(supply_hours))])
    PhD_hours = sum([s.hours for s in students if s.type == 'PhD'])
    report.append(['PhD supply: ',str(int(PhD_hours))])
    supply_sem = sum([s.hours_sem for s in students])
    report.append(['Supply per sem: ',supply_sem.__repr__()])
    report.append(['Total courses: ',str(len(courses))])
    demand_hours = sum([c.hours for c in courses])
    report.append(['Total demand: ',str(int(demand_hours))])
    demand_sem = sum([c.hours_sem for c in courses])
    report.append(['Demand per sem: ',demand_sem.__repr__()])
    #hours allocated to semester courses
    demand = {sem:sum([c.hours for c in courses if c.semester == sem]) for sem in ['Y', 'F', 'S']}
    #precentage of requested hours unfilled by student type
    requested = {t:0 for t in student_types}
    total_assigned = {t:0 for t in student_types}
    for student in students:
        requested[student.type] += student.hours
        total_assigned[student.type] += student.total_assignment()
    for t in student_types:
        if requested[t]>0:
            report.append(['Percentage of requested hours filled: '+t, str(int(100*total_assigned[t]/requested[t]))+'%'])
    '''
    #precentage of requested hours unfilled by student type, where total assignment is capped by 280
    requested = {t:0 for t in student_types}
    total_assigned = {t:0 for t in student_types}
    for student in students:
        requested[student.type] += 280
        total_assigned[student.type] += min(student.total_assignment(),280)
    for t in student_types:
        if requested[t]>0:
            report.append(['Percentage of requested hours filled (capped by 280): '+t, str(int(100*total_assigned[t]/requested[t]))+'%'])
    '''
    #Unfilled courses
    report.append(['FAILURES ',''])
    for course in courses:
        if course.remaining >0:
            report.append([colored('Unfilled! ', 'red'), str(int(course.remaining)) + 'h '+ course.__repr__()])
    #Underfunded students
    for student in students:
        if student.underfunded():
            report.append([colored('Underfunded! ', 'red'), student.__repr__() + ' pr: ' + str(student.promised)])
    return report


class Report:

    #Styles
    #regular
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    style = xlwt.XFStyle()
    style.num_format_str = '0'
    style.font = font
    #bold
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    bold = xlwt.XFStyle()
    bold.font = font
    bold.font.bold = True
    #red
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    red = xlwt.XFStyle()
    red.font = font
    red.font.colour_index = xlwt.Style.colour_map['red']
    #blue
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    blue = xlwt.XFStyle()
    blue.font = font
    blue.font.colour_index = xlwt.Style.colour_map['blue']
    #pink
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    pink = xlwt.XFStyle()
    pink.font = font
    pink.font.colour_index = xlwt.Style.colour_map['pink']
    #green
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 200
    green = xlwt.XFStyle()
    green.font = font
    green.font.colour_index = xlwt.Style.colour_map['green']
    #small
    font = xlwt.Font() 
    font.name = 'Times New Roman'
    font.size = 100
    small = xlwt.XFStyle()
    small.font = font
    #dictionary
    style_dic = {'regular':style, 'red':red, 'small':small, 'bold':bold, 'blue':blue, 'pink':pink, 'green':green}
    

    def __init__(self, name):
        self.name = name
        self.workbook = xlwt.Workbook()
        self.reports = {}

    def add_sheet(self, report, sheetname):
        self.reports[sheetname] = report
        sheet = self.workbook.add_sheet(sheetname)
        row = 0
        for line in report:
            col = 0
            new_style = self.style
            for item in line:
                if item in self.style_dic:
                    new_style = self.style_dic[item]
                else:
                    sheet.write (row, col, str(item), new_style)
                    col += 1
            row += 1

    def print(self, sheetname, output):
        if output == 'screen':
            for line in self.reports[sheetname]:
                for col in range(len(line)):
                    if col == 0:
                        line[col] = '{:<70}'.format(line[col])
                    else:
                        line[col] = '{:>30.30}'.format(line[col])
                print(''.join(line))
        if output == 'online':
            text = '<table>'+'<tr><td>'+'-------------'+'</td>'+'<td>'+sheetname.upper()+'</td>'+'<td>'+'-------------'+'</td></tr>'
            for line in self.reports[sheetname]:
                text += '<tr>'
                for element in line:
                    if not element in self.style_dic:
                        text += '<td>' + str(element) +'</td>'
                text += '</tr>'
            text += '</table>'
            print(text)

    
    def save(self, special_directory = None):
        directory = output_directory
        if special_directory != None:
            directory = special_directory
        self.workbook.save(directory + "R" + self.name + '.xls')

    def save_matching(self, matching):
        instructors, students, courses = matching.instructors, matching.students, matching.courses
        workbook = self.workbook
        style = self.style
        ls = len(students)
        lc = len(courses)
        sem_map = {s:{0:'F',  1:'S'}[s%2] for s in range(2*max(ls,lc))}
        sheet = workbook.add_sheet('Matching')
        for col in range(2,first_column+1):
            sheet.col(col).width = 1500
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(first_row+1) 
        sheet.set_vert_split_pos(first_column+1) 
        #Write courses
        sheet.write(1,first_column, 'Name', style)
        sheet.write(2,first_column, 'Instructor', style)
        sheet.write(3,first_column, 'Semester', style)
        sheet.write(4,first_column, 'Hours', style)
        sheet.write(6,first_column, 'PhDF/FHours', style)
        sheet.write(7,first_column, 'PhDS/SHours', style)
        col = first_column
        for c in range(len(courses)):
            col+=1
            course = courses[c] 
            sheet.col(col).width = 1500
            sheet.write(1,col, course.name, style)
            sheet.write(2,col, course.instructor, style)
            sheet.write(3,col, course.semester, style)
            sheet.write(4,col, course.hours, style)
            sheet.write(6,col, int(course.hours_PhD), style)
        #Write students and matching
        sheet.write(first_row,0,'Name', style)
        sheet.write(first_row,1,'Type', style)
        sheet.write(first_row,2,'Year', style)
        sheet.write(first_row,3,'Promised', style)
        sheet.write(first_row,4,'Requested', style)
        sheet.write(first_row,5,'Allocated', style)
        sheet.write(first_row,6,'eval', style)
        sheet.write(first_row,7,'#courses',style)
        sheet.write(first_row,8,'semester',style)
        row = first_row       
        t_c = 0
        course_max = 0
        students_max = []
        for s in range(len(students)):
            row +=1
            student = students[s]
            n_c=0
            col = first_column
            for ass in student.assignment:
                c = courses.index(ass[0])
                sheet.write(row, first_column + c + 1, int(ass[1]))
                assigned = True
                n_c += 1
            if n_c > course_max:
                students_max = [student]
                course_max = n_c
            elif n_c == course_max:
                students_max.append(student)
            t_c += n_c
            sheet.write(row,0,student.name, style)
            sheet.write(row,1,student.type, style)
            sheet.write(row,2,student.year, style)
            sheet.write(row,3,student.promised, style)
            sheet.write(row,4,student.hours, style)
            sheet.write(row,5,str(int(student.hours - student.remaining)), style)
            sheet.write(row,6,'{0:.2}'.format(student.quality), style)
            sheet.write(row,7,n_c, style)
            sheet.write(row,8,student.semester, style)
        last_row = row 
        for t in range(len(student_types)):
            sheet.write(last_row + 2 + t, 8, student_types[t], style)
        sheet.write(last_row + 3 + t, 8, 'fill', style)
        for c in range(len(courses)):
            course = courses[c]
            f = {t:0 for t in student_types}
            for ass in course.assignment:
                f[ass[0].type] += ass[1]
            for t in range(len(student_types)):
                row= last_row + 2 + t
                col = c + first_column + 1
                val = '{0}%'.format(int(100*f[student_types[t]]/course.hours))
                sheet.write(row, col, val, style)
            val = '{0}%'.format(int(100*sum([f[t] for t in student_types])/course.hours))
            sheet.write(row+1, col, val, style)

        sheet.write(2,4,'av.# courses', style)
        sheet.write(2,7,'{0:.2}'.format(t_c/len(students)), style)

def merge(*reports):
    n_rows = [len(r) for r in reports]
    n_reports = len(reports)
    max_rows = max(n_rows)
    report = []
    for row in range(max_rows):
        line = [''] * (n_reports+1)
        for i in range(n_reports):
            if row < n_rows[i]:
                line[0] = reports[i][row][0]
                line[i+1]=  reports[i][row][1]
        report.append(line)
    return report


class Log:

    styles = ['regular', 'red', 'small', 'bold', 'blue', 'pink', 'green']

    def __init__(self, output):
        self.contents = []
        self.output = output

    def add_line(self, line):
        self.contents.append(line)
        if self.output == 'screen':
            text = ''
            for element in line:
                if not element in self.styles:
                    text += '{:>30}'.format(element)+' '
            print(text)

    def make_last_line_bold(self):
        if self.contents != []:
            self.contents[-1].insert(0,'bold')

    

    
        
