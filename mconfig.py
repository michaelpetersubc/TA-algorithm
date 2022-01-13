
#main 
semesters = ['F','S']
other_sem = {'F':'S', 'S':'F'}
course_years = [1,2,3,4,5,6, 7] #1-4 undergrad years, 5 ug and MA, 6 - PhD, 7 important PhD courses and special assignemt
important_courses = [2100, 2101, 2200, 2201] #courses that have a special importance and hsould have priority at assignment
student_types = ['PhD', 'MA', 'JD/MA', 'MFE', 'MPP', 'NonE', 'UGNonE', 'PhDNonE', 'MANonE']
grad_student_types = ['PhD', 'MA', 'JD/MA', 'MFE']
job_title_translation = {1:'r', 2:'r', 3:'r', 4:'r', 5:'r', 6:'s', 11:'t', 12:'v', 13:'v', 14:'v', 37:'t', 41:'SO', 42:'SO' }
job_types = ['r', 't', 's', 'other', 'v', 'SO']
skill_description = ['stata', 'rs', 'history North America', 'history Europe','optz', 'game', 'stats', 'written_english', 'spoken_english', 'web', 'python', 'tablet']
#skills that are rare and important
important_skills = ['history North America', 'history Europe', 'python']
#Field description should be downloaded from table graduate_field in database
field_description = {1:'Microeconomic theory', 2:'Macroneconomic Theory', 3:'Macroeconomics', 4:'Monetary economics', 5:'Public economics', 
                    6:'Microeconomics', 7:'International economics', 8:'Applied microeconomics', 9:'Financial economics', 10:'Labour economics', 
                    11:'Economic development', 12:'Economic history', 13:'Induustrial organization',  
                    14:'Industrial organization', 15:'Econometrics', 16:'Environmental economics', 17:'Behavioural economics'}
rare_fields = ['Financial economics'] # rare fields, used in the market choice
campus_map = {1:'STG',5:'UTM'}

#Phd allotment
PhD_coeff = {1:0.35, 2:0.5, 3:0.6, 4:1, 5:1, 6:1, 7:1} #PhD coeff if allocated by year. Used in allotment, but also course.satisfacton
PhD_interval = 35  #The size of the grid to approximate PhD allotment in course.PhD_allotment)
PhD_random = False

#how much the PhD or grad hours can differ from the PhD_coeff. Course.available and course.compute_satisfaction
PhD_bracket = [0.05, 35]
grad_bracket = [0.1, 70]
def max_grad_margin_hours(h,t='PhD'):
    if t == 'PhD':
        bracket = PhD_bracket
    else:
        bracket = grad_bracket
    return max(bracket[0]*h,bracket[1])

cross_campus_preference = True #Matching.load_ta_applications:  If True, ignore cross-campus preference of students (unless clearly stated in comments or something)


alpha = 0.05 #Course importance parameter
imp = {'years':1,'hours':1.5} #Course importance parameters (Course.importance)
Y_boost = 0 #Importance boost for Y courses.IMportant to help to fill the assignments for Y courses

#### Course.utility parameters
pref_coeff = 1 #Scale of change for students in preferences 1 to 1 +  pc
boost = {'single semester':0.5, 'good experience': 1, 'field': 1, 'grad field':3, 'quality':1, 'demanded':1.5, 'type':1} 
boost_type = {'PhD':1.5, 'MA':1, 'JD/MA':1, 'MFE':0.8, 'MPP':0, 'UG':0, 'NonE':0, 'PhDNonE':0, 'MANonE':0, 'JD/MANonE':0, 'MPPNonE':0, 'UGNonE':0}
special_boost_type = 2 #used in special preferences
reject_penalty = -1

#Quality by type student.quality
quality_type = {'PhD':4.1, 'MA':3.8, 'JD/MA':3.8, 'MFE':3.3, 'MPP':3, 'NonE':3, 'UG':0}

#Components of skill match computation: Course.skill_match
s_plus = 2 # parameters of course.skill_match : penalty for student being low on skills
s_minus = 0.5 # parameters of course.skill_match : penalty for student being high on skills
skill_relevance = {'stata':0.5, 'rs':1, 'history North America':5, 'history Europe':5, 'game':1, 'optz':0.1, 'stats':1, 'written_english':0.2, 'spoken_english':0.2, 'web':0.1, 'python':5, 'tablet':0}

problematic_skill_satisfaction = {'stata':0.7, 'rs':0.7, 'history North America':1, 'history Europe':1,'optz':0.5, 'game':0.5, 'stats':0.5, 'written_english':0.5, 'spoken_english':0.5, 'web':0.5, 'python':1, 'tablet':0.6}
#Matching.course_ass_report - used to signal when trigger a problem in courses

#Utility boost from hiring a student of a given type. Now student.quality
#In principle this can be made course specific, with Commerce courses liking MFE, etc. Hence, should be course.utility 


#Priority model
#Threshold such that if the number of courses and the number of unfilled semesters is equal or bigger, then  -> priority list
#this way, nobody gets more than priority_threshold number of courses.  
priority_threshold = 4
#Boost for students who have already many assignments used in course.find_match.
many_courses_boost = 0.3

extend_good_experience = False #matching.load_courses If true, a good experience is extended across all undergrad courses with the same number
#The truoble is that it extends too much in 1st and 2nd year courses. Something to think

HIGH = 1000000

#For saving files
first_row = 10 #for saving matching in Excel sheet
first_column = 9


def clone(dic):
    return {key: dic[key] for key in dic}

    
import os

script_directory = os.path.dirname(__file__) + "/"  #<-- absolute dir the script is in
past_data_directory = script_directory + "Past data/" #<-- absolute dir where past data are
output_directory = script_directory + "Output/" #<-- absolute dir where produce is going to end up

class Parameters:

    def __init__(self):
        #Margin of semster imbalance that the policy will tolarate for students who apply to two semesters: student.available
        #The constant is actually used to define an inidvidual hours margin in StudentI.init
        self.hours_margin = {'F':35, 'S':35}
        self.old_hours_margin = {'F':70, 'S':70}
        self.one_semester_margin = {'F':35, 'S':35}
        self.hours_margin_summer ={'F':140, 'S':140}

        self.max_stretch = 15 #Maximum amount of stretch that we allow the grad students to work for above 280, if needed, i.e., if it seals the deal
        self.extra_strong_stretch = 5 #extra_strong_stretch is how much I can go above what student requested


        #Maximum regularly allowed hours
        self.max_allowed_hours = 280
        self.max_allowed_hours_summer = 140

        #Threshold used in the calculations of how valuable is availability course.find_match (or precisely, course>satisfaction_increase). 
        self.max_hours_available = 210

        #Min_remaining is equal to the min_remaining hours used in course.available. Reject match if hours >lower_minr_remaining and < min_remaining
        self.min_remaining = 20
        self.lower_min_remaining = 10

        #Threshold used to decide whether to block a match
        self.block_threshold = 0.9
        #Coefficient that allows the priority students replace the best student (if the utiliy generated by the best priority is higher han the coefficient)
        self.priority_block_threshold = 0.9

        
        #Criterion.prepare_first_list() method increases students hours from promised to requested along carefully chosen hierarchy as long as total supply 
        # is not larger than demand_threshold times the demand from courses. 
        #This parameter is quite important- if it is tightened, the algorithm does not do a good job in allocating promised hours
        self.demand_threshold_relative = 0.95
        self.demand_threshold_absolute = 2000

        #Added boost to student quality for the purpose of computing hierarchy in Criterion.prepare_first_list()
        self.type_boost_hierarchy = {'PhD':5, 'MA':4, 'JD/MA':4, 'MFE':3}

        
        self.other_grad_hours = 0.6 #Course.satisfaction - measures the value of non_PhD grad hours in the satisfaction until Phd hours are (reasonably) filled.
        self.other_hours = 0.3 #Course.satisfaction - measures the value of non_grad hours in the satisfaction until Phd hours are (reasonably) filled.


    
    def adjust_session(self, session):
        if session == 1:
            self.max_allowed_hours = self.max_allowed_hours_summer 
            self.hours_margin = self.hours_margin_summer
            k=3

global params

params = Parameters()


