
# **Description**

This document contains the description of the files and the algorithm to compute the TA assignment. I use this algorithm once a year to to create Fall?Winter TA assignment in two Economics departments of the U of Toronto. The assignment involves approximately 50,000 hours, 180 TAs, and 350 course sections. There is another Summer assignment that is much smaller (10,000 hours, and around 60-70 TAs).  

## 1. **Scripts**

The main algorithm is contained in the following scripts:

- **mMatching.py**: contains the main class *Matching* and the main loop of the algorithm,
- **mCourses.py**: contains the class *Course*, which manages courses (computations of internal variables, assigning values, etc),
- **mStudents.py**: contains the class *Student* (as well as smaller and related classes *Person* and *Instructor*), which manages information about TAs (here, a student = TA),
- **mclasses.py**: contains smaller classes  
  - *Context* that contains global variables of the algorithm,  
  - *SemesterHours* that processes pairs of numbers that represent of hour allocations across two semesters,  
  - *Market* that handles markets ((sub)lists of courses or students defined by some requirements),  
- **mconfig.py**: contains parameters of the algorithm,
- **mCriterion.py**: contains class *Criterion*, which determines the conditions of finishing a stage and the process of moving to the next stage.

The remaining scripts are peripheral to the main algorithm:

- **mrun.py**: initializes the program and sets (or loads from the command line) the main parameters,
- **mdata.py**: loads data on courses and students, and saves the assignments. This module is highly specific to the UofT Economics application,
- **mreports.py**: information reporting

## **Parameters of mrun.py**

TBA

## 2. **Data**

The algorithm loads the following data about

- instructors: name, past experience with TAs (including good experience (high evaluations) and bad experience (bad evaluations))
- courses:
  - identifiers: name, title, ids, campus (we have two campuses downtown and Mississauga),  
  - name(s) of the instructor(s),  
  - required TA hours, including minimum required hours of TAs by the type of TA. PhD students are considered most valuable, MAs and MFEs are less, and undergrads are even less.  We want to use PhD students mostly to teach graduate courses or higher year undergrad courses. However, large 1st year courses also require high-skill TAs as head TAs. The target distribution of hours by type is a part of the algorithm,  
  - TA type preference (some courses are considered appropriate for our MFE TAs),  
  - semester: F (Fall), S (Winter), Y (yearly - taught across both semesters),  
  - skills: list of required skills (with required percentage of time and skill level). Examples of skills: ability to teach history, knowledge of python, web design, Excel, etc.,
  - positive preferences: ordered list of requested TAs (max 8 now, but it is changing). This list is later supplemented with all TAs who had a good experience with the instructor,
  - negative preferences: TAs that instructor does not want. This list is supplemented with TAs whom the instructor gave low evaluations,  
  - course field: instructors classifies a course into one of the fields.
- students:
  - identifiers: name, type (PhD, different Master-level programs (MA, MFE, Law, etc), undergrad, other (which typically means non-Economics)),  
  - requested hours, up to maximum 280h (we sometimes allocate more than 280h, but it is not recommended),  
  - semester in whcih the TA wants to work: F, S, Y. If the TA wants to teach in Y semesters, we try to split their assignment equally, 
  - skills possessed,  
  - positive and negative preference over courses.
- prior assignments: The way that I work with the algorithm is running it repeatedly, finding a temporary assignment, going through it manually and making adjustments (perhaps fixing evident mistakes), fixing some of the assignments permanently, and re-running algorithm. (So, not everything is done automatically, but the algorithm managed to shorten the process that would otherwise take 3 weeks into 1 day.) The first run of the algorithm starts with *carte blanche*, but any subsequent starts with assignments that have been previously made permanent. The permanent part of the assignment is loaded as a part of data: 
  - each assignment is a tuple of student, course, and TA hours.


## 3. **Algorithm**

The computation of the TA assignment and the main is done in class *Matching*. This class is inherited from class *MatchingData* - the purpose of the latter is to load and pre-process data on courses, students, and, possibly, existing assignments.  

### <a name="MainLoop"></a> **Main loop**

The main loop of the algorithm  

- runs through a queue of courses, where the order in the queue is given by some ranking that is continuously updated and that may change in each iteration of the loop,
- tries to find a single TA for this course. The TA assignment may fill all the hours that the course needs, in which case the course is done. More likely, at least in the begining, the course will still need additional TAs, in which case, it goes back to the queue.  

The loop ends when the algorithm cannot find any more assignments for any of the courses. In such a case, the end criteria are checked, and if they are still not satisfied, some parameters of the algorithm are adjusted, and the loop starts again. If the end criteria are satisfied, or the algorithm tries all the adjustments, the process ends.  

The idea is that the courses that are high in the ranking pick TAs first, so they presumably pick the TAs who are the best, or the best matched. The longer the algorithm runs, the best TAs are already picked and the courses pick worse quality, worse matched TAs. Each time a course picks a TA, its positon in the ranking drops (but not necessarily to the bottom).

The main loop is contained in *Matching.generate_assignment()* method:

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
                self.log.add_line(['-'*20])
                end.final_results()

Before the loop:  

- active courses are set to be the entire list of courses, and there are no inactive courses,
- markets are initialized,  
- end criterion is initialized.

In the loop,  

- the most imbalanced market is chosen (see [Markets](#Markets)),
- if the demand on the market is not negative (negative demand means that current market cannot operate - see below), an course that belongs to the chosen market is selected according to a ranking that is based on the importance of the course, the number of hours already assigned for the course, etc,
- *find_match()* method tries to find a match for this course (see [Find match](#FindMatch)),
- if the assignment is unsuccessful (the method has *h=0* hours), the course is deemed inactive,
- if all courses are deemed inactive (no new assignment can be generated), or the most imbalanced market has 0 demand, the end criteria are verified by method *end.check()* (see [End criteria](#Criteria)). If the end criteria are not satisfied, adjustments to the algorithm parameters are done by the *end.check()* method and loop is restarted after making all courses active,  
- otherwise, the algorithm stops.  

### <a name="Markets"></a> **Markets**

Markets consist of courses that satisfy certain criteria. The following markets are initialized in *Matching.initialize_markets()* method:  

- for "everything",  
- courses that are taught in particular semesters F, S, Y,
- courses that require particular skill,
- courses that belong to difficult to fill fields (mostly history),
- courses that require graduate students (and do not allow for undergrad TAs).

Each market has its own method of computing demand (TA hours required by courses on the market) and supply (TA hours provided by students, who, say, have the required skill). The ratio of aggregate demand on the market to the aggregate supply is called the tightness of the market.

The main loop chooses the tightest market. The idea is that most of the time, there should be plenty of students that can fill TA hours according to a certain criteria. In fact, most of the time, the tightest market is the market for "everything." However, sometimes, some skill becomes rare relatively to the demand for this skill, and it is important for the algorithm to allocate students with this skill to courses that require such skill.  

Once the market is chosen, the method *Market.first()* chooses the course has the lowest *course.satisffaction* (see [Satisfaction](#Satisfaction)) from all courses that belong to this market.  

### <a name="Satisfaction"></a> **Course satisfaction**

Course satisfiaction is an important, continuously updated parameter of a course. It determines the order in the main loop queue, which is isued to choose the course to find the next TA assignment. 

Course satisfaction is computed in method *Course.compute_satisfaction()* according to the following formula:

                self.satisfaction = - alpha *self.importance + self.fulfillment() / PhD_coeff[self.year]

Here,  

- alpha = 0.5 is one of the mconfig.py parameters,  
- self.importance is a variable specific to each course and it is computed at the loading of data stage as a function of the total required TA hours and the course level (1st, ...,4th undergrad, master, PhD). The more important course, the lower satisfaction - and the higher position in the queue. The idea is that high-level courses, with many unfilled TA positions (our largest course typically has around 20 TAs) or PhD-level require high skilled TAs and the first pick,
- *Course.fulfillment()* is a measure of how many TA hours have been already filled:  

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

    If there are no remaining hours to be filled, fulfillment is infinite. If there are remaining hours, the fulfillment is (roughly) the fraction of hours that have been already filled, i.e., *1-(the fraction of hours that are still remaining)*. The "roughly" is because the fullfillment is higher than that formula if all PhD hours have already been filled, or all grad hours have been filled.  

    The idea is that, other things equal, courses which do not have TAs need TAs, and if they do not have enough high skill TAs, they need TAs more than courses that lack low skill TAs.  
  
### <a name="FindMatch"></a> **Find match**

The *Matching.find_match()* is another key engine of the algorithm. At the basic level, given a course **C**, the method identifies an assignment, i.e., a TA and the number of hours, that will lead to the largest increase in satisfaction (see [Satisfaction increase](#SatisfactionInc)) for the course:  

                student = max(students, key = course.satisfaction_increase)

If there is no acceptable student (the highest increase in satisfaction is less than 0), the method returns 0h, which is later interpreted as a failure by the main loop (see [Main loop](#MainLoop)). The main loop looks like this:

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

There are two exceptions to this basic idea:  

- sometimes, some students urgently need an assignment (main reason is that those students have already many ). Such students are put on a priority list, and the course **C** must pick the candidate from the priority list if their best candidate (from a complete list) is not much better. What "much better" means is stored as a parameter of the algorithm.  
- the method checks whether the chosen candidate is not a significantly better match for some other course using method *Matching.find_competition(student, course)* (see [Find competition](#FindComp)). If the competition is found, the student is assigned to the competition, and the main loop is restarted.  

If the student is a good TA, she or he is assigned to the course and the method returns the number of hours of the assignment.

### <a name="FindComp"></a> **Find competition**

This method 
If so, we say that the student and the other course form a block. The method checks all the blocks to see if there are other potential assignments *currently* available to the other course that would increase its satisfaction almost as much as the student:  

                for comp in blocks:
                    if competition == None:
                        sc = max(students, key = comp.satisfaction_increase)
                        if comp.satisfaction_increase(sc) > 0:
                            if sc == student or (not comp in sc.first_best and comp.satisfaction_increase(student, context = context) > params.block_threshold *comp.satisfaction_increase(sc, context = context)):
                                competition = compand accepts the block (i.e., matches the student with the other course) 

    If not, the block is accepted as a relevant competition, and the student is assigned to the competition:

                if competition != None:
                    h = competition.assign(student, self.log, context = context)

The identification of blocks depends on a hierarchy of potentially blocking courses that is stored as a student object: 

                block_sequence = [student.blocks_strong, student.blocks, student.demanded, student.pref]

The blocks are computed by method *Student.compute_blocks()* during the initialization phase of a student:  

                self.first_best = []
                if len(self.pref) > 1 and self.pref[0].name == self.pref[1].name:
                    self.first_best = [c for c in self.pref if c.name == self.pref[0].name]
                elif len(self.pref) > 0:
                    self.first_best = {self.pref[0]}
                self.blocks_strong = [c for c in self.first_best if self in c.pref]
                self.blocks_strong.sort(key = lambda c:(c.pref.index(self), c.importance))
                self.blocks = [c for c in self.pref if self in c.pref]
                self.blocks.sort(key = lambda c:(c.pref.index(self), -c.importance))

and they include, in a hierarchical order:  

- strong blocks: a course is a strong block for the student if it is at the top of a student preferences (including course sections with the same name), and a student is mentioned in the preferences of the course. 
- (regular) blocks: a course is a block if it is in the student preferences, and the student is in the course preferences. Strong and regular blocks are sorted by the course importance,  
- courses that demand the student, i.e., such that the student is in the course preferences,  
- student preferences, i..e, courses that are requested by the student.

The method adds all possible blocking courses in *block_sequence* from a given level of hierarchy to a list of blocks unless the course **C** belongs to this or higher level of the hierarchy:  

                for block in block_sequence:
                    if not finished and course in block:
                        finished = True
                    if not finished:
                        blocks += sorted(block, key = lambda c:c.satisfaction)

### <a name="SatisfactionInc"></a> **Satisfaction increase**

Unfortunately, increase in satisfaction is not synced with the method *Course.compute_satisfaction()*, though in principle they are related concepts. 

### <a name="Available"></a> **Available hours**

TBA

### <a name="FindMatch"></a> **Match utility**

TBA

### <a name="Criteria"></a> **End criteria**

TBA

## 4. **Diagnostics and success criteria**

TBA