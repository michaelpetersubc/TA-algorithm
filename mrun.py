#This script loads parameters of the problem 


import sys, datetime, os
from datetime import datetime
from mMatching import Matching
from mconfig import *
from mreports import Report, Log, merge

args = sys.argv
if len(args)<=1:
    args.append('21222')
    args.append('1')
    args.append('offline')

session_code = args[1]
session = int(session_code[-1])
playground = args[2] == '1'
online = args[3] == 'online'
year = 2000 + int(session_code[0:2])
print('Year: ', year)
print('Session: ', session)
print('Playground: ', playground)
print('Online: ', online)

        
def compute_matching(year=2020, session = 2, commit = False, UTM = False, by_semesters = False, which_semesters = ['F','S','Y'], econ_only = True, playground = False, online=False):
    #Process commits
    if commit:
        commit_name = datetime.datetime.now().strftime("%y-%m-%d (%H-%M-%S)") +' sessions ' + str(year) + '-' +str(year+1) + 's' + str(session)
        a = input('Are you sure you want to commit '+ commit_name + '? y/n: ')
        if not a == 'y':
            commit = False

    #Generate matchings
    #Playground variable allows to re-done the matching from scratch for testing purposes or comparison
    diagnostics = []
    output = {True:'online', False:'screen'}[online]
    log = Log(output)
    session_code = str(year-2000)+str(year-2000+1)+str(session)
    new = Matching(year, session, name = 'ALG '+session_code, econ_only = econ_only, playground = playground, log = log, online = online)
    student_summary = new.student_summary()
    new.generate_assignment()
    second_student_summary = new.student_summary()
    new.save_assignment()
    diagnostics.append(new.diagnostics())
    #old is going to load (and fix details) in the historic assignment
    if playground:
        old = Matching(year, session, name = 'Old '+session_code, econ_only = False, playground = False, log = log, online = online)
        old.generate_assignment() #this is to finish off the assignment - sometimes there are leftover unfunded students (maybe because they rejected the assignemnt and my code currently is not correcting for it)
        diagnostics.append(old.diagnostics())
        #For UTM comparison 
        if UTM:
            diagnostics.append(old.diagnostics(campus = 5))
        
    #generate Statistics report
    report = Report('TAallocation'+str(new.session_code))
    report.add_sheet(merge(*diagnostics),'Statistics')
    report.print('Statistics', output)
    report.add_sheet(log.contents, 'Log')

    if online: report.print('Log', output)

    #Generate additional offline reports
    if not online:
        matching_list = [new]
        if playground: matching_list.append(old)
        report.add_sheet(new.pecking_order_report(), 'Pecking order')
        report.add_sheet(new.student_report(), 'SR')
        if year >=2020:
            report.add_sheet(new.remaining_report(), 'Remaining')
            for i in range(len(student_summary)):
                student_summary[i] += [' '] + second_student_summary[i][4:]
            report.add_sheet(student_summary, 'SSum')
        for matching in matching_list:
            if by_semesters:
                for sem in which_semesters:
                    report.add_sheet(matching.course_ass_report([sem]),'C'+sem+matching.name)
                    report.add_sheet(matching.student_ass_report([sem]),'S'+sem+matching.name)
            report.add_sheet(matching.course_ass_report(),'Call'+matching.name)
            report.add_sheet(matching.student_ass_report(),'Sall'+matching.name)
        report.save()
        if commit:
            commit_directory = script_directory + "Commits\\"
            os.chdir(commit_directory)
            rel_commit_dir = commit_name + '\\'
            os.mkdir(rel_commit_dir)
            report.save(special_directory = commit_directory + rel_commit_dir)


compute_matching(year=year, session = session, commit = False, UTM = False, by_semesters = False, econ_only = False, online=online, playground = playground)

