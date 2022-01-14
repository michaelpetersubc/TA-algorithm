"""
How to update data (you need to be connected with Cisco vpn)
star vpn
go to vagrant directory
vagrant up
vagrant ssh
./pulldata.sh
"""
"""
With an exception of two methods establish_connectin and close_connection, 
all free stadning methods in this module are imported as class methods into class Matching in mprocess
Their purpose is to load data from SQL database. 

Class Report outputs the reports either on screen, or into an Excell spreadsheet. 
"""
import os
import xlrd
import datetime, random


from mconfig import *
from mclasses import *
from mStudents import *
from mCourses import *
from mreports import Log
from mconnection import establish_connection, close_connection

script_directory = os.path.dirname(__file__) + "\\"  #<-- absolute dir the script is in
past_data_directory = script_directory + "Past data\\" #<-- absolute dir where past data are


class MatchingData:
    
    from mreports import pecking_order_report
    from mreports import remaining_report
    from mreports import course_ass_report
    from mreports import student_ass_report
    from mreports import matching_report
    from mreports import student_report
    from mreports import student_summary
    from mreports import diagnostics

    
    def __init__(self, year, session, name = None, econ_only = True, playground = False, log = None, online = False):
        self.year = year
        self.online = online
        self.session = session
        if session == 1:
            self.date = datetime.datetime(self.year,5,1)
        else:
            self.date = datetime.datetime(self.year,9,1)
        self.year_code = (year - 2000)*100 + (year - 2000) + 1 #So, 1718 means academic year 2017/18
        self.session_code = self.year_code * 10 + session
        self.semester_string = {1:'(1,2,12)',2:'(3,4,34)'}[self.session]
        self.section_map = {} 
        self.course_map = {}
        self.student_map = {}
        self.instructor_map = {}
        if name == None:
            self.name = 'M' + str(self.session_code)
        else:
            self.name = name
        self.econ_only = econ_only
        self.playground = playground
        if log != None:
            self.log = log
        else:
            self.log = Log('screen')
        self.connection, self.cursor = establish_connection(self.log, self.online)
        self.load_instructors()
        self.load_students()
        self.load_combined_courses()
        self.load_ta_applications()
        self.process_students()
        self.load_assignment()
        close_connection(self.connection, self.cursor)

    def load_instructors(self):
        cursor = self.cursor
        self.log.add_line(['Loading instructor data ....'])
        self.instructors = []
        for instructor_number in ['1', '2']:
            query = ("SELECT phone_directory.person_id, phone_directory.name, job_title_id FROM phone_directory " 
                "INNER JOIN course_sections ON phone_directory.person_id = course_sections.instructor{2}_id "
                "INNER JOIN courses ON course_sections.course_id = courses.course_id WHERE courses.year_code = {0} and semester in {1}".format(self.year_code, self.semester_string, instructor_number) )
            cursor.execute(query)
            for (person_id, name, job_title_id) in cursor:
                if not person_id in [instructor.id for instructor in self.instructors]:
                    instructor = Instructor(person_id, name, job_title_id)
                    self.instructors.append(instructor)
                    self.instructor_map[person_id] = instructor

    def load_students(self):
        cursor = self.cursor
        self.log.add_line(['Loading main student data ....'])
        #Load main student data
        query = ("SELECT graduate.student_id, uoft_student_id, start_date, email, name, sex, program_id, degree_id, fall_semester, winter_semester, summer1_semester, summer2_semester, max_hours, stata, rs, excel, history, optz, game, stats, written_english, spoken_english, web, python, tablet, course_field1, course_field2, comment, ta_hours_fw_guaranteed, ta_hours_s_guaranteed, cont_ta_hours_fw_guaranteed, cont_ta_hours_s_guaranteed, uoft_student_id, phd_major_field_id, phd_minor_field_id, non_econ_ta_applicant  "
            "FROM ta_applications " 
            "INNER JOIN graduate ON ta_applications.student_id = graduate.student_id "
            "LEFT JOIN graduate_enrollments ON graduate_enrollments.student_id = graduate.student_id "
            "WHERE ta_applications.session = {} ".format(self.session_code))
        if self.econ_only:
            query = query + "AND (graduate.non_econ_ta_applicant IS NULL OR graduate.non_econ_ta_applicant = 0) "
        query = query + "ORDER by student_id "
        cursor.execute(query)
        self.students = []
        student_data = {}
        #the next iteration is to make sure that each student appers only once in the student list
        #in particular, only choose the record with the later enrollment date, but not later than the current year
        #the problem were students first enrolled as MAs, then becoming PhDs
        for data in cursor:
            if data[0] in student_data:
                if data[2] < self.date.date() and data[2] > student_data[data[0]][1]:
                    student_data[data[0]] = data[1:]
            else:
                student_data[data[0]] = data[1:] 
        #the next iteration creates records of students
        for student_id in student_data:
            [uoft_id, start_date, email, name, sex, program, degree, fall_semester, winter_semester, summer1_semester, summer2_semester, max_hours, stata, rs, excel, history, optz, game, stats, written_english, spoken_english, web, python, tablet, course_field1, course_field2, comment, ta_fw, ta_s, cont_fw, cont_s, uoft, major, minor, non_econ] = student_data[student_id]
            which = {sem:0 for sem in semesters}
            if self.session == 2:
                which['F'], which['S'] = fall_semester, winter_semester
            else:
                which['F'], which['S'] = summer1_semester, summer2_semester
            for sem in semesters:
                if which[sem] != 1:
                    which[sem] = 0 
            if start_date == None:
                start_year = self.year
            else: start_year = start_date.year
            if which == {sem:0 for sem in semesters} or max_hours == 0: continue
            #Correction for summer hours - summer session should count as the same year as the previous FW session
            if self.session == 2:
                s_year = self.year-int(start_year)+1
            else: 
                s_year = self.year-int(start_year)
            degree_dic = {1:'MA', 2:'MFE', 3:'PhD', 4:'ND', 5:'UG', None:' '}
            degree = degree_dic[degree]
            if program == 3:
                degree = 'JD/MA'
            if s_year == 1:
                if self.session == 2:
                    promised = ta_fw
                else: 
                    promised = ta_s
            else: 
                if self.session == 2:
                    promised = cont_fw
                else: 
                    promised = cont_s
            if non_econ in [1,2]:
                non_econ = True
            else: 
                non_econ = False
            def conv(i):
                if i == None:
                    return 0
                return i
            def conv_tablet(i):
                if i == None or i<2:
                    return 0
                return i
            history = {0:[0,0], 1:[1,0], 2:[0,1], 3:[1,1]}[conv(history)]
            skills = {'stata':conv(stata)/2, 'rs':conv(rs)/2, 'history North America':history[0], 'history Europe':history[1], 'optz':conv(optz)/2, 'game':conv(game)/2, 'stats':conv(stats)/2, 'written_english':conv(written_english)/2, 'spoken_english':conv(spoken_english)/2, 'web':conv(web)/2, 'python':conv(python)/2, 'tablet':conv_tablet(tablet)/2}
            course_fields = set()
            for field in {course_field1, course_field2}:
                if field != None and field > 0: course_fields.add(field)
            try:
                uoft_id = int(uoft_id)
            except ValueError:
                uoft_id = 0
            student = Student(student_id, uoft_id, email, name, sex, degree, non_econ, s_year, which, promised, max_hours, skills, comment, major, minor, course_fields)
            student.uoft = uoft
            self.students.append(student)
            self.student_map[student_id] = student 
        #Loading comp grades
        name_field = {1:'Micro', 3:'Macro'}
        for field in name_field:
            for y in range(2010, self.year+1):
                filename = past_data_directory + str(y) + name_field[field] + '.xlsx'
                if os.path.isfile(filename):
                    workbook = xlrd.open_workbook(filename)
                    sheet = workbook.sheet_by_name(workbook.sheet_names()[0])
                    nrows = sheet.nrows
                    grades = []
                    for row in range(nrows):
                        uoft_id = int(sheet.cell(row, 0).value)
                        score = sheet.cell(row, 1).value
                        if isinstance(score, float) or isinstance(score,int):
                            grades.append([uoft_id, score])
                    average = sum([grade[1] for grade in grades])/len(grades)
                    for grade in grades:
                        for student in self.students:
                            if student.uoft_id == grade[0]:
                                student.field_quality[field] = grade[1] / average 
        #Load MA index   
        for y in range(2010, self.year+1):
            filename = 'MA' + str(y) + '.xlsx'
            filename =  past_data_directory + filename
            if os.path.isfile(filename):
                workbook = xlrd.open_workbook(filename)
                sheet = workbook.sheet_by_name(workbook.sheet_names()[0])
                nrows = sheet.nrows
                for row in range(nrows):
                    uoft_id = int(sheet.cell(row, 0).value)
                    score = sheet.cell(row, 1).value
                    for student in self.students:
                        if student.uoft_id == uoft_id:
                            student.MA_score = score/6

    def order_list(self, l, reverse = False):
        l = sorted(l, key=lambda tup: tup[1], reverse = reverse)
        outcome = []
        for tup in l:
            if not tup[0] in outcome: outcome.append(tup[0])
        return outcome

    def load_combined_courses(self):
        cursor = self.cursor
        self.courses = []
        self.log.add_line(['Loading main course data ....'])
        query = ("SELECT t.combined_id, t.hours_f, t.hours_s, t.hours, t.phd_hours, t.grad_hours, "
                    "c.subject, c.u_number, c.g_number, c.credit, c.campus, c.title, "
                    "cs.instructor1_id, cs.instructor2_id, cs.ug_ta_hours, "
                    "IF(c.u_number IS NULL, c.g_number, c.u_number) AS sort_number "
                    "FROM talg_combined t "
                    "INNER JOIN talg_combined_sections ts ON ts.combined_id = t.combined_id "
                    "INNER JOIN course_sections cs ON ts.section_id = cs.section_id " 
                    "INNER JOIN courses c ON cs.course_id = c.course_id "
                    "WHERE t.session = {0} "
                    "GROUP BY t.combined_id "
                    "ORDER BY sort_number".format(self.session_code) )
        cursor.execute(query)
        ins_s = [instructor.id for instructor in self.instructors]
        for (combined_id, hours_f, hours_s, hours, hours_phd, hours_grad, subject, u_number, g_number, credit, campus, title, instructor1_id, instructor2_id, ug_ta_hours, sort) in cursor:
            name = ''
            if g_number == None:
                name = str(u_number)
                t= 'u'
            elif u_number == None:
                name = str(g_number)
                t = 'g'
            else: 
                name = str(u_number) + '/' + str(g_number)
                t = 'ug'
            name = name + credit + str(campus)
            if hours_f>0 and hours_s>0: 
                semester='Y' 
            elif hours_f>0: 
                semester='F' 
            else: 
                semester='S' 
            hours = SemesterHours()
            hours.h = {'F':hours_f, 'S':hours_s}
            if not isinstance(hours_phd, (int, float)): hours_phd=0 
            if not isinstance(hours_grad, (int, float)): hours_grad=0 
            allotment = {'phd':hours_phd, 'grad':hours_grad}   
            ins_list = []
            for iid in [instructor1_id, instructor2_id]:
                if iid in ins_s:
                    ins_list.append(self.instructors[ins_s.index(iid)])
            #I am not sure if this sorting below is necessary. I think it was useful for identyfying the same courses, but not anymore
            if len(ins_list)>1: 
                ins_list.sort(key = lambda i:i.name)
            course = Course(combined_id, name, u_number, g_number, subject, title, t, semester, ins_list, hours, ug_ta_hours, allotment)
            self.course_map[combined_id] = course
            self.courses.append(course)
        #Load course requirements for both instructors
        skill_records = {course.id:[] for course in self.courses}
        self.log.add_line(['Loading course requirements ....'])
        for instructor_number in ['1', '2']:
            query = ("SELECT tc.combined_id, "
                        "stata1, stata2, rs1, rs2, history1, history2, history3, optz1, optz2, game1, game2, stats1, stats2, written_english1, written_english2, spoken_english1, spoken_english2, python1, python2, web1, web2, tablet1, tablet2, r.course_field, comment "
                        "FROM instructor_ta_requirements r "
                        "LEFT JOIN courses c ON c.course_id = r.course_id "
                        "LEFT JOIN course_sections cs ON cs.course_id = c.course_id AND cs.instructor{0}_id = r.person_id "
                        "LEFT JOIN talg_combined_sections tcs ON tcs.section_id = cs.section_id "
                        "LEFT JOIN talg_combined tc ON tcs.combined_id = tc.combined_id " 
                        "WHERE tc.session = {1} AND r.session = {1} AND c.year_code = {2} and semester in {3} "
                        "GROUP BY r.requirement_id".format(instructor_number, self.session_code, self.year_code, self.semester_string))
            cursor.execute(query)
            for (combined_id, s1, s2, r1, r2, h1, h2, h3, o1, o2, g1, g2, st1, st2, w1, w2, sp1, sp2, p1, p2, w1, w2, t1, t2, course_field, comment) in cursor:
                if combined_id in skill_records:
                    history = [h1+h3,h2+h3]
                    def combine(x,y):
                        if not isinstance(x, (int, float, complex)): x = 0
                        if not isinstance(y, (int, float, complex)): y = 0
                        return (0.5*x+y)/100

                    new_skills = {'stata':combine(s1,s2), 'rs':combine(r1,r2), 'history North America':history[0]/100, 'history Europe':history[1]/100, 'optz':combine(o1,o2), 'game':combine(g1,g2),  'stats':combine(st1,st2), 'written_english':combine(w1,w2), 'spoken_english':combine(sp1,sp2), 'python':combine(p1,p2), 'web':combine(w1,w2), 'tablet':combine(t1,t2)}
                    if not isinstance(comment, str):
                        comment = ''
                    skill_records[combined_id].append([new_skills, comment])
                    self.course_map[combined_id].add_course_field(course_field)
        #Processing course requirements
        for combined_id in skill_records:
            l = len(skill_records[combined_id])
            skills = {skill:0 for skill in skill_description}
            comment = ''
            if l>0:
                record = skill_records[combined_id]
                if l == 2:
                    for skill in skill_description:
                        skills[skill] = 0.5 * record[0][0][skill] + 0.5*record[1][0][skill]
                        comment = '1.'+record[0][1] + ', 2.' + record[1][1]
                else:
                    skills = record[0][0]
                    comment = record[0][1]
            course = self.course_map[combined_id]
            course.assign_skills(skills)
            course.comment = comment
        #Load course preferences for both intructors
        self.log.add_line(['Loading course preferences ....'])
        pref_data = {}
        bad_pref_data = {}
        for instructor_number in ['1', '2']:
            query = ("SELECT tc.combined_id, p.person_id, student_id, seq FROM instructor_ta_preferences p " 
                        "LEFT JOIN instructor_ta_requirements r ON r.requirement_id = p.requirement_id "
                        "LEFT JOIN courses c ON c.course_id = r.course_id "
                        "LEFT JOIN course_sections cs ON cs.course_id = c.course_id AND cs.instructor{0}_id = r.person_id "
                        "LEFT JOIN talg_combined_sections tcs ON tcs.section_id = cs.section_id "
                        "LEFT JOIN talg_combined tc ON tcs.combined_id = tc.combined_id " 
                        "WHERE tc.session = {1} AND r.session = {1} AND c.year_code = {2} and semester in {3} "
                        "GROUP BY p.preference_id".format(instructor_number, self.session_code, self.year_code, self.semester_string))
            cursor.execute(query)
            for (combined_id, person_id, student_id, seq) in cursor:
                if student_id in self.student_map:
                    student = self.student_map[student_id]
                    if not combined_id in pref_data:
                        pref_data[combined_id] = []
                        bad_pref_data[combined_id] = []
                    if seq > 0:
                        pref_data[combined_id].append([student, seq])
                    else: 
                        bad_pref_data[combined_id].append([student, seq])
                        if person_id in self.instructor_map:
                            instructor = self.instructor_map[person_id]
                            if not student in instructor.bad_experience:
                                instructor.bad_experience.append(student)
        #Processing preference data
        for combined_id in [s for s in pref_data if s in self.course_map]:
            course = self.course_map[combined_id]
            course.pref = self.order_list(pref_data[combined_id], reverse = False)
            course.bad_pref = self.order_list(bad_pref_data[combined_id], True)
        #compute importance
        for course in self.courses:
            course.compute_importance()
        #add courses that demand students to the student demanded list 
        for course in self.courses:
            course.compute_satisfaction(context=context) 
            for student in self.students:
                if student in course.pref and not course in student.demanded:
                    student.demanded.append(course)
        
    def load_ta_applications(self):
        cursor = self.cursor
        #Load student preferences
        self.log.add_line(['Loading student preferences ....'])
        pref_data = {}
        bad_pref_data = {}
        query = ("SELECT p.student_id, tcs.combined_id, p.seq FROM ta_preferences p "
            "LEFT JOIN course_sections s ON p.course_id = s.course_id "
            "LEFT JOIN courses c ON p.course_id = c.course_id "
            "LEFT JOIN ta_applications a ON a.application_id = p.application_id "
            "LEFT JOIN talg_combined_sections tcs ON tcs.section_id = s.section_id "
            "LEFT JOIN talg_combined tc ON tc.combined_id = tcs.combined_id "
            "WHERE tc.session = {0} AND a.session = {0} AND c.year_code = {1} and s.semester in {2} ".format(self.session_code, self.year_code, self.semester_string))
        cursor.execute(query)
        for (student_id, combined_id, seq) in cursor:
            if combined_id in self.course_map:
                course = self.course_map[combined_id]
                if not student_id in pref_data:
                    pref_data[student_id] = []
                    bad_pref_data[student_id] = []
                if seq > 0:
                    pref_data[student_id].append([course, seq])
                else: 
                    bad_pref_data[student_id].append([course, seq])
        for student_id in [s for s in pref_data if s in self.student_map]:
            student = self.student_map[student_id]
            student.pref = self.order_list(pref_data[student_id], reverse = False)
            student.bad_pref = self.order_list(bad_pref_data[student_id], reverse = True)
        
        #Add cross-campus courses
        if cross_campus_preference:
            for student in self.students:
                original_pref = [c.name[:3] for c in student.pref if c.type == 'u']
                for course in self.courses:
                    if not course in student.pref and course.type == 'u' and course.name[:3] in original_pref:
                        student.pref.append(course)
                
        #Load evaluations
        query = ("SELECT e.student_id, instructor_id, e.course_id, u_number, g_number, overall, instructor_comment, year_code, date_submitted_instructor FROM ta_evaluations e " 
            "INNER JOIN ta_applications a ON a.student_id = e.student_id "
            "INNER JOIN courses c ON c.course_id = e.course_id "
            "WHERE a.session = {}".format(self.session_code))
        cursor.execute(query)
        i_ids = [instructor.id for instructor in self.instructors]
        for (sid, iid, cid, u_number, g_number, overall, comment, cyear, date) in cursor:
            if sid in self.student_map and date < self.date:
                student = self.student_map[sid]
                if iid in i_ids:
                    instructor = self.instructors[i_ids.index(iid)]
                else:
                    instructor = None
                student.evaluations.append({'instructor':instructor, 'c_id':cid, 'u_number':u_number, 'g_number':g_number, 'overall':overall, 'comment':comment})
                if overall >= 4 and instructor != None and not student in instructor.good_experience:
                    if u_number != None:
                        if u_number>=500:
                            instructor.good_experience['special'].append(student)
                        else:
                            instructor.good_experience['undergrad'].append(student)
                    if g_number != None:
                        instructor.good_experience['grad'].append(student)
                if overall in {1,2} and instructor != None and not student in instructor.bad_experience:
                    instructor.bad_experience.append(student)
        for student in self.students:
            if student.evaluations != []:
                av = sum([e['overall'] for e in student.evaluations])/len(student.evaluations)
                student.evaluation = av
            else:
                student.evaluation = 3
        for course in self.courses:
            for instructor in course.instructor_list:
                if course.u_number != None:
                    if course.u_number>=500:
                        course.good_experience += instructor.good_experience['special']
                    else:
                        course.good_experience += instructor.good_experience['undergrad'] + instructor.good_experience['grad']
                elif g_number != None:
                    course.good_experience += instructor.good_experience['grad']
            if extend_good_experience:
                for student in self.students:
                    for evaluation in student.evaluations:
                        if course.u_number != None and course.u_number == evaluation['u_number'] and not student in course.good_experience:
                            course.good_experience.append(student)
        #Find top Macro and Micro students
        self.top = {field:[] for field in field_description}
        #self.top = {field:[s for s in self.students if (field in [s.major, s.minor] or field in s.course_fields)] for field in field_description}
        for student in self.students:
            for field in student.course_fields:
                self.top[field].append(student)
        
        
        #Sort students
        def f(s):
            rank = {'PhD':'1','MA':'2', 'JD/MA':'3', 'MFE':'4', 'MPP':'5','NonE':'8', 'PhDNonE':'6', 'MANonE':'7', 'UGNonE':'9', 'UG':'9'}
            return rank[s.type]+s.name
        self.students.sort(key = f)
    
    def process_students(self):
        for student in self.students:
            student.compute_quality()
            student.compute_blocks(self.courses)
            for course in self.courses:
                if course in student.pref and not student in course.demanded:
                    course.demanded.append(student) 
        for field in field_description:
            self.top[field].sort(key = lambda s:s.quality+s.field_quality[field], reverse = True)
        #Filling extended preferences
        for course in self.courses:
            course.compute_utilities(self.students)
            #important and rare skills: history and python
            for skill in important_skills:
                for student in self.students:
                    if course.skills[skill]==1 and student.skills[skill]==1:
                        course.extended_pref.append(student)
            #graduate courses without preferences get extended preferences
            if course.type == 'g' and course.pref == []:
                course.pref = course.extended_pref
            course.compute_importance()
            course.compute_satisfaction(context=context)
            course.check_exclusions(self.students) 
            course.compute_utilities(self.students)

    def load_assignment(self):
        cursor = self.cursor
        if not self.playground:        
            query = ("SELECT a.student_id, tcs.combined_id, tcs.section_id, a.hours, a.accepted, a.new_decision FROM ta_assignments a "
                    "LEFT JOIN talg_combined_sections tcs on tcs.section_id = a.section_id " 
                    "WHERE a.session = {}".format(self.session_code))
            cursor.execute(query)
            student_map = {student.id:student for student in self.students}
            for (student_id, combined_id, section_id, hours, accepted, new_decision) in cursor:
                if combined_id in self.course_map and student_id in student_map:
                    if not ((accepted == -1 and new_decision !=-1) or new_decision == -1) and hours>0:
                        student = student_map[student_id]
                        course = self.course_map[combined_id]
                        course.assign_basic(student, hours, ['L'] + course.ass_comment(student))
                        student.assign_basic(course, hours, ['L'] + course.ass_comment(student))
                    else:
                        student = student_map[student_id]
                        student.rejected += hours
                        student.promised = max(student.promised - hours, 0)
                        student.problems.append('rejected')
                        course = self.course_map[combined_id]
                        course.add_exclusions(student)
            for course in self.courses:
                course.compute_utilities(self.students)
        #save loaded (i.e., old) assignment (for the purpose of generating reports later)
        for student in self.students:
            student.old_ass = []
            for ass in student.assignment:
                student.old_ass.append(ass)

    def save_assignment(self):
        connection, cursor = establish_connection(self.log, self.online)
        query = ("DELETE ta FROM talg_assignment ta "
        "LEFT JOIN talg_combined tc ON tc.combined_id=ta.combined_id "
        "WHERE tc.session = {0}".format(self.session_code))
        cursor.execute(query)
        query = ("ALTER TABLE talg_assignment AUTO_INCREMENT = 1")
        cursor.execute(query)
    
        values = []
        for course in self.courses:
            for ass in course.assignment:
                values.append("({0}, {1}, {2}, '{3}')".format(course.id, ass[0].id, round(ass[1]), ''.join(ass[2])))
        values = ', '.join(values)
        query = "INSERT INTO talg_assignment (combined_id, student_id, hours, comment) VALUES " + values
        cursor.execute(query)

        close_connection(connection, cursor)


    
