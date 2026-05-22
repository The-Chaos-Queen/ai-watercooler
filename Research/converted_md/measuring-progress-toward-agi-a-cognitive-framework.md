2026-03-16
Measuring Progress Toward AGI: A Cognitive
Framework
RyanBurnell1,YumeyaYamamori1,OrhanFirat1,KateOlszewska1,StephHughes-Fitt1,OranKelly1,IsaacR.
Galatzer-Levy1,MeredithRingelMorris1,AllanDafoe1,AlisonM.Snyder1,NoahD.Goodman1*,Matthew
Botvinick1* andShaneLegg1
1GoogleDeepMind,*WorkdonewhileatGoogleDeepMind.
DespitewidespreaddiscussionofAGI,thereisnoclearframeworkformeasuringprogresstowardit. This
ambiguityfuelssubjectiveclaims,makesitdifficulttotrackprogress,andriskshinderingresponsible
governance. Asastartingpointtoaddressthisgap,wepresentaframeworkforunderstandingsystem
capabilitiesinrelationtohumancognitiveabilities. Drawingfromdecadesofresearchinpsychology,
neuroscience, and cognitive science, we introduce a Cognitive Taxonomy that deconstructs general
intelligenceinto10keycognitivefaculties. Wethenproposearigorousevaluationprotocolinwhich
a system’s performance is measured across a suite of targeted, held-out cognitive tasks, generating
a ‘cognitive profile’ that can be used to understand a system’s strengths and weaknesses. We hope
thisframeworkwillprovideapracticalroadmapandaninitialsteptowardmorerigorous,empirical
evaluationofAGI.
1. Introduction
Artificialgeneralintelligence(AGI)hasthepotentialtoacceleratescientificdiscovery,increaseproduc-
tivity and help solve some of humanity’s most pressing problems. Yet our ability to understand how
close we are to this critical milestone is hampered by a lack of clarity about how general intelligence
should be operationalized and measured. As a result, the capabilities of today’s AI tools are often
underestimated or overhyped while the potential benefits and risks of future systems remain poorly
understood. This lack of empirical grounding makes it difficult for researchers to communicate
progress and for policymakers to craft effective governance, ultimately hindering our collective abil-
ity to navigate the path to AGI responsibly. To address this critical gap, we introduce a cognitive
framework for measuring progress on increasingly capable AI systems.
1.1. Operationalizing AGI
The term AGI has a long history. It was first used by Mark Gubrud in a 1997 paper to refer to
systems that "rival or surpass the human brain in complexity and speed, that can acquire, manipulate
and reason with general knowledge, and that are usable in essentially any phase of operations where a
human intelligence would otherwise be needed" (Gubrud, 1997). Then, in 2001, without knowledge of
Gubrud’s work, Shane Legg independently coined the term "Artificial General Intelligence" for Ben
Goertzel’s subsequent book, which adopted it as its title (Goertzel and Pennachin, 2007). There, AGI
was referred to as "AI systems that possess a reasonable degree of self-understanding and autonomous
self-control, and have the ability to solve a variety of complex problems in a variety of contexts, and to
learn to solve new problems that they didn’t know about at the time of their creation". Since then, AGI
has become a mainstay in discussions about AI capabilities. However, the term is often used as a
shorthand to describe various kinds of highly capable AI systems. Given the important societal and
scientific implications of generally capable AI systems, it is vital that we establish precise and robust
ways to measure progress toward this milestone.
Correspondingauthor(s):rburnell@google.com
© 2026Google.Allrightsreserved

MeasuringProgressTowardAGI:ACognitiveFramework
As a first step in this direction, in 2023 Google DeepMind presented the Levels of AGI framework
that proposed a series of important stages on the path toward general intelligence (Morris et al.,
2024). The framework considers intelligence a continuous, multidimensional construct and argues it
is important for systems to be both highly capable and highly general. On both these dimensions, it
is clear that human capabilities are a key reference point. The creation of a system that is capable
of exhibiting all the cognitive capabilities that humans have would mark a historic moment and a
philosophical milestone. Moreover, such a system would open up countless applications, including
universal assistants, personalized learning, and powerful new scientific tools.
What remains less clear is how we can understand how far away AI systems are from matching these
cognitive capabilities. Over the past few years, several benchmarks aimed at measuring progress
towardAGIhavebeenproposed(see,forexample,Chollet2019andHendrycksetal.2025). However,
existing efforts fail to cover the full breadth of human cognition and lack robust comparisons to
human performance. Here, we aim to address this gap in two parts. First, we propose a Cognitive
Taxonomy that captures the important aspects of human cognition that an AGI system should be able
to match. Second, we describe a framework for evaluating AI systems across this cognitive space to
help us better contextualize system capabilities.
2. Cognitive Taxonomy
TounderstandwhereAIsystemsstandrelativetohumancognitivecapabilities,wefirstneedtoidentify
the key cognitive processes that enable people to navigate the complex and changing world. In this
endeavor, we can turn to the decades of research into human cognition—in particular, research from
psychology, neuroscience, and cognitive science, which have built and refined theories of cognition over
many decades through iterative experimentation. These disciplines employ a wide range of methods,
including experimental paradigms, brain imaging techniques, patient studies, and computational
modeling, providing rich and empirically grounded insights we can draw from. Here, we use these
insightstocreateacognitivetaxonomy describingthecognitivecapabilitiesthatevidencesuggestsare
important for general intelligence.
Of course, characterizing intelligence is far from a simple task. Even within the field of human
cognitive science there are many debates that remain unsettled and many questions that remain
unanswered(Stainton,2006). Theworldofartificialsystemsisperhapsevenmorecomplex,richwith
amultitudeofarchitecturesandtrainingalgorithmsimprovingatapacethatmakesevolutionpalein
comparison. It is therefore possible—even likely—that some aspects of human cognition may not be
relevant in the context of artificial systems. Conversely, we are likely to find cognitive processes in
these artificial systems that humans do not possess.
For this reason, our goal was not to create the definitive account of all of cognition, but rather to
build a practical framework for evaluation that is both theoretically grounded and comprehensive
enough to cover the breadth of human intelligence. We consider this framework a starting point, and
we hope it can provide a foundation for a robust science of artificial general intelligence.
2.1. Cognitive faculties
Ourcognitivetaxonomyenumerates10cognitivefacultiesthatthescientificeffortsinmappinghuman
cognition suggest are important for intelligent behavior (see Figure 1). For each faculty and process,
we identify a set of specific abilities and sub-abilities that a generally intelligent system should be
expected to exhibit. For brevity, we provide brief descriptions of each faculty below and include the
full taxonomy in the Appendix.
2

MeasuringProgressTowardAGI:ACognitiveFramework
Animportantcharacteristicofourtaxonomyisthatitfocusesonwhatthesystemisabletoaccomplish
not on how it does so (see Marr 1982 for a discussion of this distinction). In doing so, we are able
to remain agnostic to the underlying mechanisms employed by a system and do not prescribe any
specific modeling approaches.
Figure 1 | Overviewofthe10cognitivefaculties. Facultiesoutlinedinorangerepresentcompositefaculties.
We begin with eight faculties capturing the basic building blocks of human cognition:
Perception: The ability to extract and process sensory information from the environment.
Generation: The ability to produce outputs such as speech, text, motor movements, and computer
control actions.
Attention: Theabilitytofocuscognitiveresourcesonspecificaspectsofperceptualstimuli,thoughts,
or task demands.
Learning: The ability to acquire new knowledge, skills, or understanding through experience, study,
or instruction.
Memory: The ability to store and retrieve information over time.
Reasoning: The ability to draw valid conclusions and make inferences by applying logical principles.
Metacognition: The knowledge a system has about its own cognitive processes and its ability to
monitor and control those processes.
Executive functions: Abilities that facilitate goal-directed behavior. Includes planning, inhibition,
and cognitive flexibility.
These eight faculties form the basic building blocks, but they do not operate in isolation—on the
contrary,theyinteract,overlap,worktogether,andbuildononeanother(KovacsandConway,2016).
To fully understand the capabilities of a system, we also need to understand how well it can combine
3

MeasuringProgressTowardAGI:ACognitiveFramework
and apply multiple faculties in unison. We therefore propose an additional two composite faculties
capturing two critical psychological contexts in which the various faculties are applied together:
|         |          | The ability | to find | effective | solutions |     | to domain-specific |     | problems. |     |
| ------- | -------- | ----------- | ------- | --------- | --------- | --- | ------------------ | --- | --------- | --- |
| Problem | solving: |             |         |           |           |     |                    |     |           |     |
Social cognition: Theabilitytoprocessandinterpretsocialinformationandtorespondappropriately
| in  | social situations. |     |     |     |     |     |     |     |     |     |
| --- | ------------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
We hypothesize that these ten faculties capture the key capabilities needed for a system to be both
highly general and highly capable. A system with significant weaknesses in one or more of these ten
faculties is likely to be unable to perform some real-world tasks that most humans can perform.
| 3. Evaluating |     | Cognitive |     | Capabilities |     |     |     |     |     |     |
| ------------- | --- | --------- | --- | ------------ | --- | --- | --- | --- | --- | --- |
To understand the cognitive capabilities of an AI system, we need to robustly evaluate the system
across each cognitive faculty and compare the system to a meaningful human baseline. We therefore
| propose | the following | three-stage |     | evaluation | protocol: |        |         |       |              |        |
| ------- | ------------- | ----------- | --- | ---------- | --------- | ------ | ------- | ----- | ------------ | ------ |
| 1.      |               |             |     | of the     | system    | across | a broad | suite | of cognitive | tasks. |
| Conduct | cognitive     | assessment  |     |            |           |        |         |       |              |        |
2. on the same cognitive tasks to establish a point of comparison.
| Collect | human | baselines |     |     |     |     |     |     |     |     |
| ------- | ----- | --------- | --- | --- | --- | --- | --- | --- | --- | --- |
3. Build cognitive profiles to map the system’s strengths and weaknesses in relation to human
performance.
| 3.1. Conduct |     | cognitive | assessment |     |     |     |     |     |     |     |
| ------------ | --- | --------- | ---------- | --- | --- | --- | --- | --- | --- | --- |
The first step in evaluating progress toward AGI is to evaluate system performance on a broad
suite of cognitive tasks covering each faculty. The cognitive tasks should be:
• abilities. It is important to include tasks that isolate each
| Targeted  | to      | specific | cognitive |           |          |       |             |     |     |     |
| --------- | ------- | -------- | --------- | --------- | -------- | ----- | ----------- | --- | --- | --- |
| cognitive | faculty | in order | to        | precisely | diagnose | model | weaknesses. |     |     |     |
• Heldout. Evaluationsshouldideallyuseprivate,held-outtestsetstopreventcontamination—if
systems had previously seen solutions or strategies for the specific test items, then performance
on those tests is unlikely to be indicative of general intelligence (e.g., see Jacovi et al. 2023).
• Independently verified. To ensure the community can be confident in the findings, both the
cognitive tasks and the evaluation results should be audited by an independent third party.
• humans. Some tasks are easy for humans and hard for AI systems (see
| Varied | in difficulty | for |     |     |     |     |     |     |     |     |
| ------ | ------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Chollet et al. 2025), so it is important to include such tasks as well as tasks that test the limits
| of  | human capabilities. |     |     |     |     |     |     |     |     |     |
| --- | ------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
• format. Idiosyncrasies in the structure of specific tasks can artificially
| Varied | in structure | and |     |     |     |     |     |     |     |     |
| ------ | ------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
inflate(orinhibit)performanceonthosetasks(thisistruebothforhumansandAIsystems;e.g.
see Cheng and Holyoak 1985; Dasgupta et al. 2024). For this reason, the evaluation of each
faculty should include multiple tasks with a variety of structures and formats (e.g. multiple
choice vs open response, text inputs vs multimodal, multi-step vs single-turn).
| 3.2. Collect | human |     | baselines |     |     |     |     |     |     |     |
| ------------ | ----- | --- | --------- | --- | --- | --- | --- | --- | --- | --- |
To understand how close a system’s capabilities are to human-level on a set of tasks, we need to
|          |                   |     | on  | those | same tasks. |     |     |     |     |     |
| -------- | ----------------- | --- | --- | ----- | ----------- | --- | --- | --- | --- | --- |
| quantify | human performance |     |     |       |             |     |     |     |     |     |
4

MeasuringProgressTowardAGI:ACognitiveFramework
These human baselines can be constructed by asking a large sample of humans to complete the same
tasks as the AI systems. The tasks should be performed under the same conditions, including the
same task instructions (and few-shot examples, if any), response format, and access to external tools.
Because we want to understand the full range of human capabilities, we think it is critical to sample
widely from the human population. At the same time, we want to understand how well systems will
perform in real-world situations—situations that involve knowledge and abilities that are typically
only fully developed in adulthood and typically honed through formal education. Therefore, we
| propose | that  | a reasonable |     | human     | baseline   | should | consist | of a      |                 |     |                |
| ------- | ----- | ------------ | --- | --------- | ---------- | ------ | ------- | --------- | --------------- | --- | -------------- |
|         |       |              |     |           |            |        |         |           | demographically |     | representative |
| sample  | of    | with         | at  | least the | equivalent | of     | an      |           |                 |     | 1.             |
|         |       | adults       |     |           |            |        | upper   | secondary | education       |     |                |
| 3.3.    | Build | cognitive    |     | profiles  |            |        |         |           |                 |     |                |
Using the evaluation results from the cognitive assessment and the human baselines, we can next
build cognitive profiles for each system to map out the strengths and weaknesses of the system
| relative | to  | human | performance |     | across | the 10 cognitive | faculties. |     |     |     |     |
| -------- | --- | ----- | ----------- | --- | ------ | ---------------- | ---------- | --- | --- | --- | --- |
To do so, we can calculate the percentage of people from the human sample the system outperforms,
and place the system along the distribution of human performance (see Figure 2 for examples).
Giventhejaggednatureofsystemcapabilities(Morrisetal.,2026),manykindsofprofilesarepossible.
For example:
1. Asystemscoresbelowthehumanbaselinesamplemedianforoneormorecognitivefaculties.
Such a system shows significant cognitive weaknesses and is likely to struggle in at least some
|     | real-world  | contexts. |       |     |       |          |        |        |        |     |                      |
| --- | ----------- | --------- | ----- | --- | ----- | -------- | ------ | ------ | ------ | --- | -------------------- |
|     | 2. A system | scores    |       |     |       |          |        |        | across |     | cognitive faculties. |
|     |             |           | above | the | human | baseline | sample | median |        | all | ten                  |
Such a system is demonstrating the ability to match the cognitive capabilities of at least 50% of
the human sample, and is likely to perform well in many real-world contexts.
3. A system scores in the across cognitive faculties (Figure 2C). Such a
|     |     |     |     | 99th | percentile |     | all | ten |     |     |     |
| --- | --- | --- | --- | ---- | ---------- | --- | --- | --- | --- | --- | --- |
system is demonstrating it can match almost anyone from the human sample across the entire
cognitivespace.2 Ofcourse,anypracticalhumanbaselinesample—evenahighlyrepresentative
one—is unlikely to capture the full scope of human capabilities, so further scrutiny would be
|     | required | before | drawing | any | conclusions |     | based on | this pattern. |     |     |     |
| --- | -------- | ------ | ------- | --- | ----------- | --- | -------- | ------------- | --- | --- | --- |
Some important methodological notes are warranted here: To construct a cognitive profile, we need
to calculate an overall score for each person and each AI system on each faculty (see Figure 2).
There are many ways these scores could be calculated. The simplest approach would be to aggregate
together the metrics from each cognitive task within a faculty. But taking a more sophisticated
statistical approach—such as building an Item-Response Theory model of system capabilities (see
e.g., Martínez-Plumed et al. 2019)—could provide more robust and informative results.
Regardlessofwhichapproachisused,itisimportanttoquantifytheuncertaintyaroundeachcapability
estimate. Uncertainty in this context stems from at least three main sources:
1. quality: Factors such as prompt quality and task diversity can dramatically affect how
Task
|     | informative |     | the results | are. |     |     |     |     |     |     |     |
| --- | ----------- | --- | ----------- | ---- | --- | --- | --- | --- | --- | --- | --- |
1Equivalenttoearningahigh-schooldegreeintheUS.
2Asomewhatstrongertestwouldbetorequirethesystemtoscoreatorabovethesamplemaximumacrosseveryfaculty.
Butitisdifficulttoquantifytheuncertaintyaroundamaximumvalue.
5

MeasuringProgressTowardAGI:ACognitiveFramework
2. Construct validity: Cognitive evaluations are intended to provide insights into broad cognitive
faculties, such as reasoning or attention. However, if the datasets do not isolate the target
facultyeffectivelyorthedataarecontaminated,theresultsmaynotaccuratelyreflectasystem’s
general capabilities.
3. Stochasticity: The stochasticity of generative AI systems adds noise to evaluation results—
asking a system to complete the same task multiple times can produce wildly different results
across repetitions (this is particularly true of complex tasks with multiple steps).
Characterizing this uncertainty is crucial for understanding the extent to which differences between
systems or between a system and the human sample are meaningful.
Figure 2 | Cognitiveprofilesforthreehypotheticalsystems. PanelA:Ahypotheticalsystemthatshowssignificant
cognitiveweaknessesrelativetothehumansample. PanelB:Ahypotheticalsystemthatoutperformsthehuman
samplemedianacrossallcognitivefaculties. PanelC:Ahypotheticalsystemthatoutperformsthehumansample
maximumacrossallcognitivefaculties. Thehypotheticalhumansamplescoresarestandardizedforeachdimension
forillustrativepurposes.
6

MeasuringProgressTowardAGI:ACognitiveFramework
4. Discussion
4.1. Building cognitive evaluations
Here we provide a framework for measuring AI systems across the range of human cognitive capabili-
ties. To execute on this framework, we need robust cognitive benchmarks. Many useful benchmarks
already exist for some parts of the cognitive space, including problem solving (Phan et al., 2025),
perception (Patraucean et al., 2023), and world knowledge (Cheng et al., 2025; Haas et al., 2025).
But there are large coverage gaps in areas such as metacognition, attention, learning, and social
cognition. Moreover, many of the high-quality benchmarks that do exist are fully public, so they are
susceptible to data contamination and may not provide generalizable signal. For this reason, we do
not think existing benchmarks are sufficient to reliably evaluate AI cognitive capabilities.
To address these gaps, we are working with the academic community to build robust, held-out
evaluations that will better enable us to evaluate increasingly capable AI systems.
4.2. Beyond cognitive faculties
Our taxonomy focuses on cognitive capabilities. But to build a full understanding of AI capabilities
and AI behavior we will need to consider—and evaluate—many other system characteristics. Below
we discuss several that we think will be important, all of which can be understood in relation to a
human baseline.
4.2.1. Processing and response speed
For a response to be adaptive or useful, correctness is not always sufficient. Often, the response must
be timely, too. Take, for example, a self-driving car system. The system’s reliability depends not only
on its ability to identify potential hazards, but its ability to do so quickly. Even when speed is less
critical,itisstillimportantforunderstandingreal-worldutility—asystemthatcanfixacodingbugor
bookaflightinoneminuteislikelytobemuchmoreusefulthanonethattakessixhourstocomplete
the task.
The construct of processing speed is at least partly cognitive (Danthiir et al., 2005)—for example,
problemsolvingspeeddependsonthethinkingstrategiesasystememploysandonhowwellitdraws
connections to relevant knowledge. But speed also depends on other factors such as hardware and
network speed, so it does not fit perfectly as a cognitive faculty. Regardless, response speed is a key
performance metric that should be measured across the cognitive space.
4.2.2. System propensities
Another important determinant of how a system will behave when deployed is its propensities (i.e.
not just what the system can do but what it will tend to do). How willing is the system to take risks?
How aligned is it with human values? What are its typical problem-solving strategies? How does it
communicateandinteractwithpeople? Thesekindsofbehavioralfactorswillsignificantlyaffecthow
safe and reliable that system is, so we need robust tools to evaluate them. A full account of system
propensitiesisbeyondthescopeofthispaper,butwillbeacriticalareaofstudytoinformdeployment
decisions and enable effective governance (see e.g. Romero-Alvarado et al. 2026; Taubenfeld et al.
2026).
7

MeasuringProgressTowardAGI:ACognitiveFramework
4.2.3. Creativity
The human capacity for creativity has long been a topic of interest to both philosophy and cognitive
science. Yet disagreements continue about how creativity should be conceptualized and measured
(see e.g. Boden 1994; Kaufmann 2003). One common way of thinking about creative outputs is that
they need to be both novel and high-quality (Sternberg and Lubart, 1998). But whether an output is
high quality is highly subjective and domain specific, especially when it has entirely novel features.
Moreover,itcanbearguedthatthesecharacteristicsaresimplygeneralfeaturesofintelligentbehavior.
Forthisreason,itmaybedifficulttoisolateandevaluatecreativityobjectivelyinAIsystems. However,
we can still evaluate the cognitive processes involved in creativity. For example, creativity is often
associatedwithcognitiveflexibility(theabilitytoswitchmodesofthinkingandtheabilitytogenerate
a wide variety of distinct ideas), which is covered in the taxonomy as part of executive functions. In
addition,thetaxonomycapturesworldknowledge(aspartofsemanticmemory)andproblemsolving,
both of which are relevant to creativity (Sternberg and Lubart, 1998).
4.2.4. End-to-end deployment evaluations
Lastly, it is important to make clear that cognitive benchmarking is not a substitute for applied,
end-to-end evaluations—if a system is being deployed in a specific context, it is absolutely critical to
evaluatethesystemonimportantdeploymentworkflows. Thesetwoapproachesarecomplementary—
cognitive evaluations can help explain model failures and inform model improvements; real-world,
deployment evaluations can inform deployment decisions and predict economic impacts (see, e.g.
Mazeika et al. 2025; Patwardhan et al. 2025).
4.3. Model vs system evaluation
Historically, evaluations were largely focused on a specific model checkpoint. But modern AI systems
are more than just a model—they are deployed with specific system instructions, have access to tools,
can manipulate their environments via actions, and may even have the ability to make calls to other
AI systems.
How should we approach evaluations in light of this added complexity? We think that attempting to
isolate the core model of a system from its other components will become increasingly impractical
since the inner workings of new systems are often not disclosed and these different components may
not even be easily separable. This model-only approach will also become less and less informative,
sincetheresultswouldnotberepresentativeofhowthesystemwilloperateorperformwhendeployed
with access to these components. Modularity is also not unique to artificial systems—after all, the
humanbrainhasvariouscognitivesystemsandmoduleswithdifferent(butinterconnected)functions
(Yeoetal.,2011). Wethereforethinkthebestapproachistoevaluatethesystemasawhole,including
any built-in tools or modules.
Measuring intelligence as a property of the system does have its drawbacks, though. For example,
one difficult ramification is that the intelligence attributed to a given model depends on the harness
built around it—analogous to concluding that a person becomes more intelligent when given access
to a calculator or a computer. In addition, this approach raises questions about how to construct
informative cognitive tests. When testing humans, access to external tools is typically restricted
to maintain control over the testing conditions and target specific cognitive processes. If we allow
AI systems to have access to any and all tools during evaluations, these tools could muddy the
interpretation of the findings. For instance, imagine we want to test semantic memory for historical
events. If the system can simply search the internet for information about these events, we are no
longer measuring the system’s memory—only its ability to search the internet. These are thorny
8

MeasuringProgressTowardAGI:ACognitiveFramework
issues that require consideration for each individual cognitive test. At the very least, any human
baseline studies should ensure that participants are given access to the same tools we expect the AI
systems to employ.
4.4. Validation and iteration
Like any science, the science of artificial general intelligence will be iterative in nature. The cognitive
taxonomy described here is very much a starting point—it seems certain that AI systems will go
on to develop cognitive capabilities that do not map neatly onto our taxonomy. Indeed, AI systems
already possess some capabilities not found in humans, such as LiDAR perception and native image
generation. Future iterations of this taxonomy will need to explore how to identify, characterize, and
incorporate these emergent components of intelligence.
We also still have much to learn about how specific cognitive faculties are related to real-world
performance. If a system lags behind humans in one or more of the 10 faculties, it would clearly
demonstrate the system cannot match the generality of human intelligence. But what would a
weakness in a given faculty mean when the system is deployed in the real world? There are good
theoretical reasons to expect that each one of the 10 cognitive capacities identified here is important
for different aspects of real-world performance. For example, a system that cannot plan would likely
struggle with long-horizon, multi-step tasks, while a system deficient in social understanding is likely
to perform poorly in situations that involve complex interactions with people. But empirical work is
still needed to demonstrate these relationships and to further understand the importance of each
cognitive capacity when it comes to practical, real-world tasks.
5. Conclusion
The pursuit of Artificial General Intelligence represents a pivotal moment for humanity. By providing
a clear, empirical framework rooted in the established science of human cognition, we aim to move
the conversation around AGI from one of subjective claims and speculation toward a grounded,
measurable scientific endeavor. Our Cognitive Taxonomy and evaluation protocol offer a way to map
the jagged landscape of AI capabilities and track progress toward general intelligence.
9

MeasuringProgressTowardAGI:ACognitiveFramework
| 6. Contributors | and | Acknowledgments |     |     |
| --------------- | --- | --------------- | --- | --- |
Contributors
Alex Siegman Dima Yeroshenko Martin Polacek Viorica Patraucean
Alëna Aksënova Edward Loper Martyna Płomecka Virginia Aglietti
AnastasiosKementsiet- Ellie Pavlick Mor Hazan Taege William Cunningham
| sidis           | Evan          | Rosen     | Nicholas Cain  | William Isaac |
| --------------- | ------------- | --------- | -------------- | ------------- |
| Arjun Narayanan | Georgi        | Karadzhov | Nico Duduta    | Xin Liu       |
| Ashwin Vaswani  | Jed           | McGiffin  | Rasmi Elasmar  | Yao Yan       |
| Bernd Bohnet    | Joe           | Heyward   | Reut Aharony   | Yuan Yuan     |
| Chrysovalantis  | Anasta- Julia | Haas      | Rivka Moroshko |               |
| siou            | Kartikeya     | Badola    | Silvia Chiappa |               |
| Claire Yao      | Kate          | Lin       | Steve Zheng    |               |
| Daniel McDuff   | Laura         | Kampis    | Vik Sharma     |               |
This effort involved the contributions of many individuals across Google, including researchers,
engineers, and operations staff. We gratefully acknowledge the dedication and hard work of each
contributor on this effort. Contributors are listed in alphabetical order.
We are grateful for the invaluable feedback from Dharshan Kumaran, Joel Z Leibo, Ellie Pavlick, Mike
Mozer, Martin Chadwick, Zoubin Ghahramani, Rohin Shah, Iason Gabriel, Lucy Cheke, and Jose
Hernandez-Orallo.
10

MeasuringProgressTowardAGI:ACognitiveFramework
| 7.  | Appendix: |     |     | Cognitive |     | taxonomy |     |     |     |     |     |
| --- | --------- | --- | --- | --------- | --- | -------- | --- | --- | --- | --- | --- |
7.1. Perception
Theabilitytotakeinandprocesssensoryinformationfromtheworldsuchasimages,audio,andtext
(Harris and Smith, 2022). Perception allows a system to observe the environment and respond to its
characteristics.3 We organize this section by modality, and include aspects of language processing in
| the    | relevant | modality.  |     |     |     |     |     |     |     |     |     |
| ------ | -------- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7.1.1. | Visual   | perception |     |     |     |     |     |     |     |     |     |
The ability to take in and process visual information from light (Cornsweet, 1970; Haber and
| Hershenson, |     | 1973). |     |     |     |     |     |     |     |     |     |
| ----------- | --- | ------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Low-level visual perception The ability to detect and identify surface-level features of visual
4
| information, |     | such | as light | intensity, |     | color, and | contrast. |     |     |     |     |
| ------------ | --- | ---- | -------- | ---------- | --- | ---------- | --------- | --- | --- | --- | --- |
• Lightdetection: Theabilitytodetectthebrightnessofdifferentpartsofavisualscene(Gilchrist
|     | et al., | 1999). |     |     |     |     |     |     |     |     |     |
| --- | ------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
• The ability to detect contrast between light and dark areas of an
|     | Contrast |       | (edge) | detection: |        |          |     |                     |     |     |     |
| --- | -------- | ----- | ------ | ---------- | ------ | -------- | --- | ------------------- | --- | --- | --- |
|     | image    | (Marr | and    | Hildreth,  | 1980). | Critical | for | image segmentation. |     |     |     |
• Color detection: Theabilitytodistinguishbetweendifferentcolorsinanimage(Gegenfurtner,
2003).
• Depth perception: The ability to identify the distance to objects in a visual scene (Parker,
2007).
• The ability to detect movement in a dynamic visual scene (Borst and
|     | Motion    | detection: |        |     |     |     |     |     |     |     |     |
| --- | --------- | ---------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
|     | Egelhaaf, |            | 1989). |     |     |     |     |     |     |     |     |
• Shape detection: The ability to identify and locate simple shapes in an image (Biederman,
|            | 1987;     | Todd,       | 2004).     |          |        |            |          |            |                |              |       |
| ---------- | --------- | ----------- | ---------- | -------- | ------ | ---------- | -------- | ---------- | -------------- | ------------ | ----- |
|            |           |             |            |          | The    | ability to | process, | interpret, | and understand | the semantic | mean- |
| High-level |           | visual      | perception |          |        |            |          |            |                |              |       |
| ing        | of visual | information |            | (Ullman, | 1996). |            |          |            |                |              |       |
• Objectrecognition: Theabilitytoidentifyandcategorizeobjectsinavisualscene(Riesenhuber
|     | and | Poggio, | 2000). |     |     |     |     |     |     |     |     |
| --- | --- | ------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
• Visual spatial localization: The ability to determine the spatial location of objects in a visual
|     | scene | (Hollingworth, |     | 2007). |     |     |     |     |     |     |     |
| --- | ----- | -------------- | --- | ------ | --- | --- | --- | --- | --- | --- | --- |
• The ability to determine the number of objects or entities in a visual scene
|     | Visual | counting: |           |        |     |     |     |     |     |     |     |
| --- | ------ | --------- | --------- | ------ | --- | --- | --- | --- | --- | --- | --- |
|     | (Trick | and       | Pylyshyn, | 1994). |     |     |     |     |     |     |     |
• Static scene understanding (image understanding): The ability to form a high-level under-
standing of events appearing in a static visual scene (Epstein and Baker, 2019).
|     | •       |     |       |               |     |        |                 |     | The ability | to form | a high-level |
| --- | ------- | --- | ----- | ------------- | --- | ------ | --------------- | --- | ----------- | ------- | ------------ |
|     | Dynamic |     | scene | understanding |     | (video | understanding): |     |             |         |              |
understanding of events occurring in a dynamic visual scene (Zacks et al., 2010).
3Inputmodalitiesarehighlysystemdependent.Asystemmaynotneedtoperceiveallmodalitiestobehaveintelligently,
althougheachadditionalmodalityofinformationislikelytoprovidesomebenefits.
4Here,weclassifyabilitiesaslow-levelperceptionwhentheyinvolve“surface-level”processingwithlittlesemantic
interpretation.Conversely,weclassifyabilitiesthatrequiredeeper,semanticprocessingashigh-levelvisualperception.This
isbecausethereisevidenceinhumansthathigh-levelandlow-levelperceptualprocessingcanbedissociated(e.g.Farah
1990).However,thedividinglineissomewhatfuzzy—perceptualabilitiesfallonaspectrumfromthosewhichrequirevery
littlesemanticprocessing(e.g.,contrastdetection)tothosewhicharehighlyreliantonsemanticprocessing(e.g.,scene
understanding).
11

MeasuringProgressTowardAGI:ACognitiveFramework
• Word segmentation: The ability to segment and identify letters and words in a visual scene
| (Norris, | 2013). |     |     |     |     |     |
| -------- | ------ | --- | --- | --- | --- | --- |
• The ability to understand the meaning of language presented in a
| Reading         | comprehension: |                 |     |     |     |     |
| --------------- | -------------- | --------------- | --- | --- | --- | --- |
| visual form     | (Kendeou       | et al., 2016).5 |     |     |     |     |
| 7.1.2. Auditory | perception     |                 |     |     |     |     |
The ability to take in and process auditory information from sound waves (Warren, 1982).
Theabilitytoextractsurface-levelfeaturesofauditoryinformation
| Low-level Auditory | perception |                   |     |     |     |     |
| ------------------ | ---------- | ----------------- | --- | --- | --- | --- |
| such as loudness,  | pitch, and | spatial location. |     |     |     |     |
• Loudness detection: The ability to identify the loudness (volume) of a sound (Fechner, 1860).
• Pitch detection: The ability to identify the pitch of a sound (Oxenham, 2012).
• The ability to differentiate components of an auditory scene occurring
| Sound discrimination: |     |     |     |     |     |     |
| --------------------- | --- | --- | --- | --- | --- | --- |
simultaneously, such as different sounds or speakers (Bizley and Cohen, 2013).
• Sound localization: The ability to identify the direction of a sound and the distance to its
| source (Blauert, | 1996). |     |     |     |     |     |
| ---------------- | ------ | --- | --- | --- | --- | --- |
• The ability to separate a stream of sound information into separate
| Speech        | segmentation: |     |     |     |     |     |
| ------------- | ------------- | --- | --- | --- | --- | --- |
| words (Brent, | 1999).        |     |     |     |     |     |
• Rhythm perception: The ability to identify patterns or rhythms in sound information (Grahn,
2012).
|                     |            | The ability | to process, | interpret, and | understand | auditory infor- |
| ------------------- | ---------- | ----------- | ----------- | -------------- | ---------- | --------------- |
| High-level Auditory | perception |             |             |                |            |                 |
mation.
• Speech comprehension: The ability to understand the meaning of spoken language (Diehl
| et al., 2004). |     |     |     |     |     |     |
| -------------- | --- | --- | --- | --- | --- | --- |
• The ability to recognize and distinguish individual speakers (McDer-
| Speaker      | identification: |     |     |     |     |     |
| ------------ | --------------- | --- | --- | --- | --- | --- |
| mott, 2009). |                 |     |     |     |     |     |
• Sound recognition: The ability to recognize different types of sounds.
| •        |                      | Theabilitytounderstandandinterpreteventsoccurringinan |     |     |     |     |
| -------- | -------------------- | ----------------------------------------------------- | --- | --- | --- | --- |
| Auditory | scene understanding: |                                                       |     |     |     |     |
| auditory | scene (Bregman,      | 1994).                                                |     |     |     |     |
• Listening comprehension: The ability to understand the meaning of language presented in
| auditory               | form (Friederici, | 2002).6 |     |     |     |     |
| ---------------------- | ----------------- | ------- | --- | --- | --- | --- |
| 7.1.3. Text perception |                   |         |     |     |     |     |
The ability to process, interpret, and understand information presented as text.
Unlike humans, who perceive text only through other modalities (e.g. through vision via reading, or
through touch via braille reading), today’s AI systems perceive text as an entirely separate modality
via tokenization and embedding. These processes are flawed and lossy much like other forms of
perceptual processing (Shin and Kaneko, 2024)—as illustrated by systems’ difficulties with spelling
(how many r’s are in strawberry, again?) and their brittleness to perturbations in text inputs.
5Todemonstratereadingcomprehension,asystemneedstoshowmasteryofatleastonelanguage.Theabilitytolearn
newlanguagesiscoveredunderlearning,andthenumberoflanguagesasystemknowsisafunctionofitssemanticmemory.
6Aswithreadingcomprehension,todemonstratelisteningcomprehensionasystemneedstoshowmasteryofatleast
onelanguage.Theabilitytolearnnewlanguagesiscoveredunderlearning,andthenumberoflanguagesasystemknows
isafunctionofitsworldknowledge.
12

MeasuringProgressTowardAGI:ACognitiveFramework
Althoughtextperceptionisnotstrictlyafundamentalcapabilitythathumanshave,textualinformation
is central to today’s society and is an essential part of how today’s systems are trained to understand
language and the world. The ability to bypass vision and directly perceive text-based language
is a fascinating and unique property of today’s AI systems. Language models have demonstrated
that this ability can enable remarkable performance on a range of tasks, so we think it is worthy of
considerationandmeasurement. Ofcourse,thelackofadirectequivalentinhumansraisesquestions
about how text perception should factor into judgments about AGI. In one sense, this ability can be
thought of as an "easier" version of reading, without the need to segment the visual information into
letters and words. Therefore, we think that an AGI should, at a minimum, be able to comprehend a
given text at least as well as a human could if presented with that text in visual form.
Low-level text perception The ability to extract surface-level features from text inputs such as
| letters and | words. |     |     |     |     |     |
| ----------- | ------ | --- | --- | --- | --- | --- |
• The ability to discriminate between different symbols in a stream of
| Symbol     | discrimination: |             |           |     |     |     |
| ---------- | --------------- | ----------- | --------- | --- | --- | --- |
| characters | (e.g.           | letters and | numbers). |     |     |     |
• Word segmentation: The ability to segment a stream of characters into words.
|            |                 | The | ability to process, | interpret, and | understand | text information. |
| ---------- | --------------- | --- | ------------------- | -------------- | ---------- | ----------------- |
| High-level | text perception |     |                     |                |            |                   |
• The ability to understand the meaning of language presented as
| Language | comprehension: |              |        |     |     |     |
| -------- | -------------- | ------------ | ------ | --- | --- | --- |
| text     | (Traxler and   | Gernsbacher, | 2006). |     |     |     |
• Code comprehension: The ability to understand the meaning and function of written code.
| 7.1.4. Other | modalities | of perception |     |     |     |     |
| ------------ | ---------- | ------------- | --- | --- | --- | --- |
There are many other types of perception seen in humans or other animals that may provide utility
for AI systems. It seems likely that each additional modality of perception will provide some useful
information to systems that can help them navigate the real world. For example, touch (de Haan and
Dijkerman,2020),smell(Stevenson,2009),andtemperatureperception(Jungetal.,2023)couldall
prove highly useful for a system designed to help with cooking or manufacturing. Still, the relative
importance of these modalities for intelligent behavior remains unclear, so in this initial version of
the taxonomy we do not include them in detail. These modalities are nonetheless worth considering,
both for researchers building new systems and those building model evaluations.
| 7.1.5. Multi-sensory |     | integration |     |     |     |     |
| -------------------- | --- | ----------- | --- | --- | --- | --- |
The ability to integrate information from multiple modalities together. Because different perceptual
modalities provide complementary information about features such of the environment, such as
form, location, size, and speed of movement, multi-sensory integration helps enable joint processing,
reasoning,andplanningacrosstheinformation(ZmigrodandHommel,2013). Thisabilityshouldbe
| measured | for each combination | of  | modalities. |     |     |     |
| -------- | -------------------- | --- | ----------- | --- | --- | --- |
7.2. Generation
The ability to generate outputs such as text, speech, or actions such as motor movements, computer
control actions, or tool use calls. Output generation is critical for a system’s ability to communicate
| and complete | tasks effectively. |     |     |     |     |     |
| ------------ | ------------------ | --- | --- | --- | --- | --- |
13

MeasuringProgressTowardAGI:ACognitiveFramework
Theabilitytogeneratehigh-qualityoutputscanbeatleastpartlydecoupledfromtheabilitytodecide
which output to generate (imagine a very savvy but poorly-skilled tennis player who might correctly
determine the best shot to play but fail miserably to execute that shot effectively). In other words,
output generation captures a system’s ability, not its ability to reason and plan about which
execution
| actions | to attempt.     |     |     |     |     |     |
| ------- | --------------- | --- | --- | --- | --- | --- |
| 7.2.1.  | Text generation |     |     |     |     |     |
Theabilitytogeneratetextoutputs. Inhumans,textgenerationisindirect,typicallymediatedthrough
motor actions (via writing or typing), but in AI systems text can be a direct output.
Natural language generation The ability to generate natural language in text form. Typically
known as language in cognitive science (Garrett, 1988; Pickering and Garrod, 2013).
production
• Grammatical correctness: The ability to produce grammatically correct sentences.
• The ability to select appropriate words to convey rich meaning.
| Lexical | selection: |     |     |     |     |     |
| ------- | ---------- | --- | --- | --- | --- | --- |
Code generation The ability to generate structurally and syntactically correct code (see Fedorenko
| et al. 2019 | for a discussion). |               |        |         |     |     |
| ----------- | ------------------ | ------------- | ------ | ------- | --- | --- |
| 7.2.2.      | Audio generation   |               |        |         |     |     |
| The ability | to produce         | audio outputs | (i.e., | sound). |     |     |
Theabilitytogeneratenaturalandexpressivespeech(TraxlerandGernsbacher,
Speechgeneration
2006).
| • Clarity:  | The | ability to clearly | pronounce   | words      | and phonemes. |                    |
| ----------- | --- | ------------------ | ----------- | ---------- | ------------- | ------------------ |
| •           |     |                    | The ability | to produce | grammatically | correct sentences. |
| Grammatical |     | correctness:       |             |            |               |                    |
• The ability to select appropriate words to convey rich meaning.
| Lexical | selection: |     |     |     |     |     |
| ------- | ---------- | --- | --- | --- | --- | --- |
• Prosody control: The ability to control the rhythm of speech such as pitch, stress, speed and
intonation.
• The ability to express a wide range of emotions through variation in
| Emotional | expression: |     |     |     |     |     |
| --------- | ----------- | --- | --- | --- | --- | --- |
prosody.
| 7.2.3.      | Action generation |         |                 |                  |     |     |
| ----------- | ----------------- | ------- | --------------- | ---------------- | --- | --- |
| The ability | to generate       | actions | that manipulate | the environment. |     |     |
Motor control The ability to control a body or robotic actuators (Nishikawa et al., 2007).
The ability to produce computer control actions such as key presses and mouse
| Computer  | control |                |     |     |     |     |
| --------- | ------- | -------------- | --- | --- | --- | --- |
| movements | (Smith  | et al., 1999). |     |     |     |     |
Tool use The ability to use external objects, systems, or resources to assist in the pursuit of goals
(Baber, 2003).
| 7.2.4. | Thought generation |     |     |     |     |     |
| ------ | ------------------ | --- | --- | --- | --- | --- |
Theabilitytogenerateinternalthoughtswhichcanbeusedtoguidedecisions(HolyoakandSpellman,
1993). Thoughts could take the form of language, images (akin to human visual imagination), or
| could take | a more | abstract form. |     |     |     |     |
| ---------- | ------ | -------------- | --- | --- | --- | --- |
14

MeasuringProgressTowardAGI:ACognitiveFramework
By definition thoughts are internal in nature and may be difficult or impossible to evaluate. However,
conscious thought is critical for human problem solving and there is substantial evidence for its value
in AI systems (Comanici et al., 2025; OpenAI, 2024), so evaluating the features and quality of a
| system’s | thoughts | will | almost | certainly | be enlightening. |
| -------- | -------- | ---- | ------ | --------- | ---------------- |
7.3. Attention
The ability to focus cognitive resources on specific aspects of perceptual stimuli, information, or
thoughts (Styles, 2006; Treisman, 1969). This is critical when a system is faced with a complex
| environment |     | and has | limited | cognitive | resources. |
| ----------- | --- | ------- | ------- | --------- | ---------- |
Thereisadelicatebalancebetweentheneedtoavoiddistractionbynarrowlyfocusingoninformation
thatisimportantforcurrentgoalsandtheneedtostayattentivetothewiderenvironmenttorespond
when unexpected changes or stimuli appear (Burgoyne and Engle, 2020; Engle, 2018).
| 7.3.1. | Attention | capacity |     |     |     |
| ------ | --------- | -------- | --- | --- | --- |
The amount of information a system can focus on simultaneously. This capacity may be different for
different modalities or types of information (e.g., text, images, audio; Cowan et al. 2005; Fritz et al.
2007).
| 7.3.2. | Selective | attention |     | / Attentional | control |
| ------ | --------- | --------- | --- | ------------- | ------- |
Theabilitytoselectivelyfocusoninformationthatisrelevanttocurrentgoalsandignoreinformation
that is goal-irrelevant (Theeuwes, 1991). This active, top-down form of attention is important for
effective goal-driven behavior and is often considered an executive function.
Sustainedattention Theabilitytomaintainfocusongoal-relevantinformationovertime(Esterman
| and Rothlein, |     | 2019; | Sarter | et al., 2001). |     |
| ------------- | --- | ----- | ------ | -------------- | --- |
The ability to ignore distracting or goal-irrelevant perceptual information
| Perceptual      | inhibition |     |          |        |     |
| --------------- | ---------- | --- | -------- | ------ | --- |
| (Van Moorselaar |            | and | Slagter, | 2020). |     |
Attention shifting The ability to actively shift attention from one location or piece of information
| to another | (Brown          | and | Tait,     | 2016). |     |
| ---------- | --------------- | --- | --------- | ------ | --- |
| 7.3.3.     | Stimulus-driven |     | attention |        |     |
The ability for attention to be directed in a "bottom-up" way toward new stimuli or environmental
changes (Awh et al., 2012; Katsuki and Constantinidis, 2014). This is crucial for quickly identifying
| situational | shifts | that | require | a response. |     |
| ----------- | ------ | ---- | ------- | ----------- | --- |
7.4. Learning
The ability to acquire new knowledge, skills, or behaviors through experience, study, or instruction.
Learning is vital for a system’s ability to adapt to new situations or environmental changes (Ginsburg
andJablonka,2010;Morand-Ferron,2017).7 Here,weenumerateseveralimportantkindsoflearning
| an AGI | should | be able | to employ. |     |     |
| ------ | ------ | ------- | ---------- | --- | --- |
7Formanycurrentsystems,learningoccursonlyduringtrainingorin-context.However,fortrulyrobustandadaptive
behavior,AIsystemsshouldbeabletolearn(andretain)newknowledgeandskillsovertime(e.g.,aspartofacontinuous
learningprocess).
15

MeasuringProgressTowardAGI:ACognitiveFramework
| 7.4.1. Concept | formation |     |     |
| -------------- | --------- | --- | --- |
The ability to abstract the key features of objects, events, and ideas to form categories, concepts,
schemas, and scripts (Bruner, 1986; Gershman and Niv, 2010; Goodman et al., 2008; Tenenbaum
| et al., 2011).     | Important | for generalization. |     |
| ------------------ | --------- | ------------------- | --- |
| 7.4.2. Associative | learning  |                     |     |
The ability to learn the relationships between events, objects or stimuli that appear together (Shanks,
1995).
| 7.4.3. Reinforcement |     | learning (Operant | conditioning) |
| -------------------- | --- | ----------------- | ------------- |
The ability to learn based on the consequences (rewards and punishments) of specific actions or
| situations           | (Skinner, 1963; | Sutton et al., | 1998). |
| -------------------- | --------------- | -------------- | ------ |
| 7.4.4. Observational |                 | learning       |        |
The ability to learn by watching others perform a skill or task (Bandura, 2008).
| 7.4.5. Procedural | learning |     |     |
| ----------------- | -------- | --- | --- |
The ability to learn skills, action patterns, or tasks through performance or practice (Cohen and
8
Squire, 1980).
| 7.4.6. Language | learning |     |     |
| --------------- | -------- | --- | --- |
The ability to learn new language-related information, such as syntax and vocabulary (Bates, 1976;
Chomsky,1965;Pinker,1994;Saffran,2003). Includesnaturallanguagesaswellascodinglanguages
| and tool use | frameworks. |     |     |
| ------------ | ----------- | --- | --- |
7.5. Memory
The ability to keep track of information over time (Squire and Kandel, 1999). Memory and learning
are closely linked—the distinction is that learning is focused on the acquisition of new knowledge,
whereas memory is concerned with the ability to maintain that knowledge over time. Evaluating
memory typically involves testing a system’s pre-existing knowledge as well as its ability to store and
retrieve newly-learned information. The quality of a system’s memory can be considered in terms of
how much information a system can remember, how long the information can be maintained, and/or
are.9
| how accurate | the memories |     |     |
| ------------ | ------------ | --- | --- |
Givenhowcloselylinkedlearningandmemoryare,itmaybedifficulttoseparatethemwhenevaluating
system capabilities. However, there are at least some failure modes that are specific to one or the
other. For example, a failure to update semantic knowledge despite being able to successfully recall
already stored knowledge would be considered a failure of learning, while forgetting information
over time that was initially successfully learned would be a failure of memory.
8In
humans, procedural learning can be dissociated from the ability to learn facts and other explicit information
(Willinghametal.,1989).
9Mostresearchonhumanmemoryisfocusedonunderstandingthespecificmemorymechanismsofthebrain,suchas
“long-termmemory”and“short-termmemory”.ButthesemechanismsarespecifictohumansandmaynotberelevanttoAI
systems.Forthisreason,wethinkitisimportanttoremainagnostictotheunderlyingmemoryimplementationandfocus
onevaluatinghowwellasystemcankeeptrackofinformationovertime.
16

MeasuringProgressTowardAGI:ACognitiveFramework
| 7.5.1. Semantic | memory | (World knowledge) |     |
| --------------- | ------ | ----------------- | --- |
The ability to keep track of facts and other general information not tied to a specific episode (Kumar,
| 2021; Yee | et al., 2013). |     |     |
| --------- | -------------- | --- | --- |
Commonsenseknowledge Knowledgeaboutthefundamentalrules,properties,andcharacteristics
| of the world. | Includes:         |     |     |
| ------------- | ----------------- | --- | --- |
| • General     | knowledge         |     |     |
| • Causal      | knowledge         |     |     |
| • Temporal    | knowledge         |     |     |
| • Spatial     | knowledge         |     |     |
| • Intuitive   | physics knowledge |     |     |
Domainknowledge Specialistknowledgeaboutspecificsubjectsordomains(Ericssonetal.,2018).
For example:
| • Linguistic      | knowledge |     |     |
| ----------------- | --------- | --- | --- |
| • STEM            | knowledge |     |     |
| • Coding          | knowledge |     |     |
| • Legal           | knowledge |     |     |
| • Financial       | knowledge |     |     |
| • Medical         | knowledge |     |     |
| • Historical      | knowledge |     |     |
| • Social-cultural | knowledge |     |     |
| 7.5.2. Episodic   | memory    |     |     |
The ability to keep track of information relating to specific events, including the sensory information
(images, sounds, etc.) associated with those events (Conway, 2009; Tulving et al., 1972).10
The ability to keep track of sensory information from specific events (e.g. visual,
| Sensory   | memory                     |     |     |
| --------- | -------------------------- | --- | --- |
| auditory, | or olfactory information). |     |     |
Temporal memory The ability to keep track of the sequence and temporal relationships between
events.
The ability to keep track of the spatial relationships between objects from specific
Spatial memory
| events (e.g.      | their positions, | orientations, | and movements). |
| ----------------- | ---------------- | ------------- | --------------- |
| 7.5.3. Procedural | memory           |               |                 |
Theabilitytokeeptrackoftheactionandoutputpatternsneededtoperformskills(CohenandSquire,
1980).
| 7.5.4. Prospective | memory |     |     |
| ------------------ | ------ | --- | --- |
The ability to remember to perform a planned action when a specific cue arises, such as a moment in
time or in response to a specific event (e.g. “When I go to the store, I should remember to get milk”;
10Theabilitytoremembersensoryinformationissometimesseparatedfromtheabilitytorememberfactualdetails
aboutspecificevents.Therelationshipbetweentheseaspectsofeventmemoryiscomplex,soforpracticalpurposesweuse
episodicmemorytorefertobothtogether.
17

MeasuringProgressTowardAGI:ACognitiveFramework
| McDaniel | and Einstein | 2007). |     |     |
| -------- | ------------ | ------ | --- | --- |
7.5.5. Forgetting
The ability to remove outdated, wrong, or irrelevant information from memory. This could involve
information compression or wholesale pruning of specific memories. Forgetting is important for
| efficient | storage and | retrieval (Bjork, | 1989). |     |
| --------- | ----------- | ----------------- | ------ | --- |
7.6. Reasoning
The ability to draw valid conclusions by applying logical principles or drawing inferences. (Leighton
and Sternberg, 2003; Rips, 1990). Typically, automatic pattern matching would not be considered
reasoning.
| 7.6.1. Deductive | (logical) | reasoning |     |     |
| ---------------- | --------- | --------- | --- | --- |
Theabilitytoreasonfromasetofpremises,rulesorfactstoreachalogicalconclusion(Johnson-Laird,
1999). Adefiningfeatureofdeductionisalackofambiguity—aslongasonecanbesurethepremises
aretrue,thencorrectlyapplieddeductionwillleadtoconclusionsthatarecertain. Deductionrequires
a grasp of logical concepts such as negation, “AND”, “OR”, “XOR”, and “ALL”.
| 7.6.2. Inductive | reasoning |     |     |     |
| ---------------- | --------- | --- | --- | --- |
The ability to draw general conclusions based on a specific set of facts, information, or observations
(e.g., “The sun has risen every day so far; therefore, the sun will rise tomorrow”).
Unlike deductive reasoning, these general conclusions are probabilistic, not certain. As a result,
induction can occasionally lead us astray. However, in a world in which there is constant uncertainty,
inductive reasoning is essential to avoid constant paralysis (Heit, 2000).
| 7.6.3. Abductive | reasoning |     |     |     |
| ---------------- | --------- | --- | --- | --- |
The ability to make inferences about the best or most likely explanation for a set of observations.
Much like inductive reasoning, abductive reasoning is uncertain. A key feature of abduction is that it
involves the generation of new explanatory hypotheses, rather than just generalizing from a set of
| observations      | (Bhagavatula | et al., | 2020). |     |
| ----------------- | ------------ | ------- | ------ | --- |
| 7.6.4. Analogical | reasoning    |         |        |     |
The ability to identify similarities between situations or concepts and to use those similarities to
draw conclusions about unknown properties of one based on known information about the other
| (Alexander          | et al., 2016; | Gentner and | Maravilla, | 2018). |
| ------------------- | ------------- | ----------- | ---------- | ------ |
| 7.6.5. Mathematical |               | reasoning   |            |        |
The ability to perform mathematical calculations and operations (Gilmore et al., 2018). Includes
| basic arithmetic | and | algebra. |     |     |
| ---------------- | --- | -------- | --- | --- |
18

MeasuringProgressTowardAGI:ACognitiveFramework
7.7. Metacognition
The knowledge a system has about its own cognitive processes, and its ability to monitor and control
| those processes      | (Dunlosky | and Metcalfe, | 2009; | Tarricone, | 2011). |     |     |
| -------------------- | --------- | ------------- | ----- | ---------- | ------ | --- | --- |
| 7.7.1. Metacognitive |           | knowledge     |       |            |        |     |     |
Metacognitive knowledge is a system’s self-knowledge about its own abilities, limitations, knowledge,
learning processes, and behavioral tendencies (Flavell, 1979; Tarricone, 2011). In some ways,
metacognitive knowledge could simply be considered a special case of world knowledge.
Knowledge of limitations Knowledge of one’s own capabilities and limitations (Fleming and Daw,
| 2017; Fleming | and Lau,    | 2014).         |               |           |                              |                  |      |
| ------------- | ----------- | -------------- | ------------- | --------- | ---------------------------- | ---------------- | ---- |
|               |             |                | Knowledge     | of        | one’s own learning processes | and the factors  | that |
| Knowledge     | of learning | processes      |               |           |                              |                  |      |
| can assist    | or impair   | learning (Binz | et al., 2024; | Wang,     | 2021).                       |                  |      |
|               |             |                |               | Knowledge | about the information        | stored in memory |      |
| Metamemory    | (Knowledge  | of knowledge)  |               |           |                              |                  |      |
and about the processes involved in storing or retrieving that information (Nelson, 1990).
Knowledge of behavioral patterns Knowledge of one’s own tendencies and behavioral patterns
| (Grant, 2001;        | Vazire | and Carlson, | 2010). |     |     |     |     |
| -------------------- | ------ | ------------ | ------ | --- | --- | --- | --- |
| 7.7.2. Metacognitive |        | monitoring   |        |     |     |     |     |
Theabilitytomonitorthestateofcognitiveprocesses(e.g.,evaluatingthestateoflearningorcurrent
| performance) | (Dunlosky | and Metcalfe, | 2009; | Nelson, | 1990). |     |     |
| ------------ | --------- | ------------- | ----- | ------- | ------ | --- | --- |
The ability to accurately estimate the likelihood that an action will be
| Confidence | calibration |     |     |     |     |     |     |
| ---------- | ----------- | --- | --- | --- | --- | --- | --- |
successful or that a response will be correct (Fleming and Lau, 2014; Harvey, 1997; Yeung and
| Summerfield, | 2012) |     |     |     |     |     |     |
| ------------ | ----- | --- | --- | --- | --- | --- | --- |
The ability to monitor progress when learning new information (Arbuckle
| Judgments  | of learning   |       |     |     |     |     |     |
| ---------- | ------------- | ----- | --- | --- | --- | --- | --- |
| and Cuddy, | 1969; Rhodes, | 2016) |     |     |     |     |     |
Error monitoring The ability to notice when errors are made (Yeung and Summerfield, 2012).
The ability to judge where a piece of information was generated or learned
Source judgments
| from (Johnson        | et al., | 1993; Mitchell | and Johnson, |     | 2000) |     |     |
| -------------------- | ------- | -------------- | ------------ | --- | ----- | --- | --- |
| 7.7.3. Metacognitive |         | control        |              |     |       |     |     |
A model’s ability to utilize insights from metacognitive knowledge and monitoring to adjust cognitive
processes or strategies (e.g. by switching learning strategy based on the kinds of errors that one is
making; Botvinick 2007; Nelson 1990; Son and Schwartz 2002). Sometimes considered an executive
function.
The ability to adjust action patterns or strategies to correct errors (Metcalfe,
Error correction
2017).
Learningstrategyselection Theabilitytoselectappropriatelearningstrategiesbasedonmetamem-
ory and judgments of learning (e.g. terminating study of well-learned information to focus on
information that has not yet been well-learned) (Dunlosky et al., 2013).
19

MeasuringProgressTowardAGI:ACognitiveFramework
| 7.8. | Executive |     | functions |     |     |     |     |
| ---- | --------- | --- | --------- | --- | --- | --- | --- |
Higher-order cognitive abilities that enable goal-directed behavior by regulating and orchestrating
| thoughts |      | and actions | (Diamond, |             | 2013). |     |     |
| -------- | ---- | ----------- | --------- | ----------- | ------ | --- | --- |
| 7.8.1.   | Goal | setting     | and       | maintenance |        |     |     |
The ability to set and maintain goals to organize and direct action (Buschman and Miller, 2014;
| Dickinson |     | and Balleine, |     | 1994). |     |     |     |
| --------- | --- | ------------- | --- | ------ | --- | --- | --- |
7.8.2. Planning
The ability to formulate sequences of future actions to achieve specific goals (Owen, 1997). Planning
is a key part of solving multi-step or long-term problems. The process of planning can be broadly
construed as building up (and pruning) some kind of decision-tree (Mattar and Lengyel, 2022).
| 7.8.3. | Inhibitory |     | control |     |     |     |     |
| ------ | ---------- | --- | ------- | --- | --- | --- | --- |
Theabilitytochange,withhold,orsuppresslearnedorhabitualresponsesinfavorofmorecontrolled,
| goal-appropriate |           |     | ones (Bari  | and | Robbins, | 2013; Miyake | et al., 2000). |
| ---------------- | --------- | --- | ----------- | --- | -------- | ------------ | -------------- |
| 7.8.4.           | Cognitive |     | flexibility |     |          |              |                |
Theabilitytoswitchbetweendifferenttasks,concepts,orwaysofthinking(BraemandEgner,2018).
| 7.8.5. | Conflict | resolution |     |     |     |     |     |
| ------ | -------- | ---------- | --- | --- | --- | --- | --- |
Theabilitytomanageandresolveconflictinginformation,contradictorygoals,orcompetingresponses
to select an appropriate action (Botvinick et al., 2001; Veen and Carter, 2006). Not to be confused
| with   | social  | conflict | resolution. |     |     |     |     |
| ------ | ------- | -------- | ----------- | --- | --- | --- | --- |
| 7.8.6. | Working | memory   |             |     |     |     |     |
The ability to manipulate information internally in service of a goal (e.g. performing intermediate
calculations while solving a problem or mentally rotating an image to consider it from a different
perspective) (Baddeley, 1992). Although the name would suggest this ability is a subset of memory,
in truth working memory involves the coordination of multiple faculties including memory, attention,
| and  | sometimes | reasoning |         | (Engle, | 2002). |     |     |
| ---- | --------- | --------- | ------- | ------- | ------ | --- | --- |
| 7.9. | Problem   |           | solving |         |        |     |     |
Asthenamesuggests,thisbroadabilityreferstotheabilitytosolveproblemsandovercomeobstacles
(Mayer and Wittrock, 2006). This is a composite ability that relies heavily on planning, reasoning,
| and | in-context | learning. |     | Problem | solving | requires: |     |
| --- | ---------- | --------- | --- | ------- | ------- | --------- | --- |
• Understanding and representing the problem (e.g. via perception and abstraction)
• Identifyingandretrievingrelevantknowledge(e.g.,facts,analogousepisodes,meta-knowledge
|     | about      | effective | problem-solving |         |         | strategies). |     |
| --- | ---------- | --------- | --------------- | ------- | ------- | ------------ | --- |
|     | • Breaking | down      | the             | problem | into    | sub-goals    |     |
|     | • Planning | a         | sequence        | of      | actions | to take      |     |
20

MeasuringProgressTowardAGI:ACognitiveFramework
| • Executing | the plan | (e.g. via reasoning | + output generation) |     |     |     |
| ----------- | -------- | ------------------- | -------------------- | --- | --- | --- |
It would be impossible to enumerate all types of problems that humans are able to solve, but we
| describe     | several important | types below. |     |     |     |     |
| ------------ | ----------------- | ------------ | --- | --- | --- | --- |
| 7.9.1. Fluid | reasoning         |              |     |     |     |     |
The ability to identify patterns and apply them to solve novel problems. Relies on a mix of deductive,
| inductive,          | and abductive | reasoning (Cattell, | 1943; Kent, 2017). |     |     |     |
| ------------------- | ------------- | ------------------- | ------------------ | --- | --- | --- |
| 7.9.2. Mathematical |               | problem solving     |                    |     |     |     |
Applying mathematical concepts and techniques to solve problems (Schoenfeld, 1985).
| 7.9.3. Algorithmic | problem | solving |     |     |     |     |
| ------------------ | ------- | ------- | --- | --- | --- | --- |
Solving logical problems using algorithmic techniques—a key part of writing code.
| 7.9.4. Commonsense |     | problem solving |     |     |     |     |
| ------------------ | --- | --------------- | --- | --- | --- | --- |
Solvingreal-worldproblemsbyapplyinggeneralknowledgeandeverydayunderstandingoftheworld
| (Brachman | and Levesque,   | 2022).        |               |                |               |        |
| --------- | --------------- | ------------- | ------------- | -------------- | ------------- | ------ |
|           |                 | Understanding | and reasoning | about temporal | concepts such | as the |
| Temporal  | problem solving |               |               |                |               |        |
order and duration of events, time-based relationships, and temporal constraints.
Reasoning about the relationships between objects in space, including
| Spatial          | problem solving |                |     |     |     |     |
| ---------------- | --------------- | -------------- | --- | --- | --- | --- |
| their positions, | orientations,   | and movements. |     |     |     |     |
Causal problem solving Reasoningaboutcause-and-effectrelationshipsbetweeneventsorentities.
Reasoning about basic physical principles and how objects behave in the world.
| Intuitive | physics       |     |     |     |     |     |
| --------- | ------------- | --- | --- | --- | --- | --- |
| Includes  | concepts such | as: |     |     |     |     |
| • Object  | permanence    |     |     |     |     |     |
• Gravity
• Momentum
• Force
| 7.9.5. Knowledge | discovery |     |     |     |     |     |
| ---------------- | --------- | --- | --- | --- | --- | --- |
The ability to generate novel hypotheses, experiments, and solutions to scientific questions (Dunbar,
| 2001; Klahr, | 2000; Nersessian, | 2002). |     |     |     |     |
| ------------ | ----------------- | ------ | --- | --- | --- | --- |
| 7.10.        | Social cognition  |        |     |     |     |     |
Theabilitytoprocessandinterpretsocialinformationandtorespondappropriatelyinsocialsituations.
Crucial for interacting with people or other systems (Higgins and Bargh, 1987).
21

MeasuringProgressTowardAGI:ACognitiveFramework
| 7.10.1. | Social perception |     |     |     |
| ------- | ----------------- | --- | --- | --- |
Theabilitytointerpretsocialcuesbasedonperceptualinformationsuchasfacialexpressions,toneof
| voice, or | body language  | (Tajfel, 1962). |     |     |
| --------- | -------------- | --------------- | --- | --- |
| 7.10.2.   | Theory of mind |                 |     |     |
Theabilitytoreasonaboutthementalstatesofothers,includingbeliefs,desires,emotions,intentions,
expectations, and perspectives. Theory of mind is important for the ability to predict and explain
| others’ | behavior (Frith and | Frith, 2005; | Leslie et | al., 2004). |
| ------- | ------------------- | ------------ | --------- | ----------- |
| 7.10.3. | Social skills       |              |           |             |
The ability to recognize, understand, and act according to social norms or expectations (Chung and
Rimal, 2016).
The ability to work together with others toward common goals (Rand and Nowak,
Cooperation
2013).
Theabilitytoworktogetherwithotherstowardgoalsthataremisalignedorinconflict.
Negotiation
| (Bazerman | et al., 2000). |     |     |     |
| --------- | -------------- | --- | --- | --- |
Deception The ability to mislead others by hiding or disguising intentions or actions in order to
achieve goals (Spence et al., 2004). Could be considered a harmful capability depending on the
context.
Persuasion The ability to influence others’ attitudes, beliefs, or behaviors (Wood, 2000). Could be
| considered | a harmful capability | depending | on the | context. |
| ---------- | -------------------- | --------- | ------ | -------- |
22

MeasuringProgressTowardAGI:ACognitiveFramework
References
P. A. Alexander, D. Dumas, E. M. Grossnickle, A. List, and C. M. Firetto. Measuring relational
reasoning. The Journal of Experimental Education, 84(1):119–151, 2016. doi: 10.1080/00220973.
2014.963216. URL https://doi.org/10.1080/00220973.2014.963216.
T. Y. Arbuckle and L. L. Cuddy. Discrimination of item strength at time of presentation.
Journal of
| experimental | psychology, | 81(1):126, | 1969. |     |     |     |
| ------------ | ----------- | ---------- | ----- | --- | --- | --- |
E. Awh, A. V. Belopolsky, and J. Theeuwes. Top-down versus bottom-up attentional control: A failed
| theoretical | dichotomy. |     |     | sciences, | 16(8):437–443, | 2012. |
| ----------- | ---------- | --- | --- | --------- | -------------- | ----- |
Trends in cognitive
C. Baber. Cognition and tool use: Forms of engagement in human and animal use of tools. CRC Press,
2003.
| A. Baddeley. | Working memory. |     | Science, 255(5044):556, |     | 1992. |     |
| ------------ | --------------- | --- | ----------------------- | --- | ----- | --- |
A.Bandura. Observationallearning. InTheinternationalencyclopediaofcommunication.WileyOnline
| Library, | 2008. |     |     |     |     |     |
| -------- | ----- | --- | --- | --- | --- | --- |
A.BariandT.W.Robbins. Inhibitionandimpulsivity: behavioralandneuralbasisofresponsecontrol.
|          | neurobiology, | 108:44–79, | 2013. |     |     |     |
| -------- | ------------- | ---------- | ----- | --- | --- | --- |
| Progress | in            |            |       |     |     |     |
E. Bates. Language and context: The acquisition of pragmatics. Academic Press, 1976.
M.H.Bazerman,J.R.Curhan,D.A.Moore,andK.L.Valley. Negotiation. Annualreviewofpsychology,
| 51(1):279–314, | 2000. |     |     |     |     |     |
| -------------- | ----- | --- | --- | --- | --- | --- |
C. Bhagavatula, R. L. Bras, C. Malaviya, K. Sakaguchi, A. Holtzman, H. Rashkin, D. Downey, S. W.-t.
| Yih, and | Y. Choi. Abductive |     | commonsense | reasoning, | 2020. | URL |
| -------- | ------------------ | --- | ----------- | ---------- | ----- | --- |
https://arxiv.org/abs/
1908.05739.
I. Biederman. Recognition-by-components: a theory of human image understanding.
Psychological
| review, | 94(2):115, 1987. |     |     |     |     |     |
| ------- | ---------------- | --- | --- | --- | --- | --- |
M.Binz,I.Dasgupta,A.K.Jagadish,M.Botvinick,J.X.Wang,andE.Schulz. Meta-learnedmodelsof
| cognition. |            |           | Sciences, | 47:e147, | 2024. |     |
| ---------- | ---------- | --------- | --------- | -------- | ----- | --- |
|            | Behavioral | and Brain |           |          |       |     |
J. K. Bizley and Y. E. Cohen. The what, where and how of auditory-object perception. Nature
Reviews Neuroscience, 14(10):693–707, Oct 2013. ISSN 1471-0048. doi: 10.1038/nrn3565. URL
https://doi.org/10.1038/nrn3565.
R.A.Bjork. Retrievalinhibitionasanadaptivemechanisminhumanmemory,pages309–330. Varieties
of memory and consciousness: Essays in honour of Endel Tulving. Lawrence Erlbaum Associates,
Inc, Hillsdale, NJ, US, 1989. ISBN 0-89859-935-0 (Hardcover); 0-8058-0546-X (Paperback).
J. Blauert. Spatial Hearing: The Psychophysics of Human Sound Localization. The MIT Press, 10
1996. ISBN 9780262268684. doi: 10.7551/mitpress/6391.001.0001. URL
https://doi.org/
10.7551/mitpress/6391.001.0001.
M. A. Boden. What is creativity? In M. A. Boden, editor, Dimensions of Creativity, pages 75–117. The
MIT Press, Cambridge, MA, 1994. ISBN 9780262023689. doi: 10.7551/mitpress/2437.003.0006.
A. Borst and M. Egelhaaf. Principles of visual motion detection. Trends in neurosciences, 12(8):
| 297–306, | 1989. |     |     |     |     |     |
| -------- | ----- | --- | --- | --- | --- | --- |
23

MeasuringProgressTowardAGI:ACognitiveFramework
M. M. Botvinick. Conflict monitoring and decision making: reconciling two perspectives on anterior
cingulate function. Cognitive, Affective, & Behavioral Neuroscience, 7(4):356–366, 2007.
M. M. Botvinick, T. S. Braver, D. M. Barch, C. S. Carter, and J. D. Cohen. Conflict monitoring and
| cognitive      | control. | Psychological |           | review,  | 108(3):624, |          | 2001.  |     |             |     |            |     |        |
| -------------- | -------- | ------------- | --------- | -------- | ----------- | -------- | ------ | --- | ----------- | --- | ---------- | --- | ------ |
| R. J. Brachman | and      | H. J.         | Levesque. |          |             |          |        |     |             |     | Sense. The | MIT | Press, |
|                |          |               |           | Machines |             | like Us: | Toward | AI  | with Common |     |            |     |        |
Cambridge, MA, 2022. ISBN 9780262369237. doi: 10.7551/mitpress/14299.001.0001. URL
https://doi.org/10.7551/mitpress/14299.001.0001.
S.BraemandT.Egner. Gettingagriponcognitiveflexibility. Currentdirectionsinpsychologicalscience,
| 27(6):470–476, |          | 2018. |       |           |                |     |              |     |        |     |        |       |     |
| -------------- | -------- | ----- | ----- | --------- | -------------- | --- | ------------ | --- | ------ | --- | ------ | ----- | --- |
| A. S. Bregman. |          |       |       |           |                |     |              |     | sound. | MIT | press, | 1994. |     |
|                | Auditory |       | scene | analysis: | The perceptual |     | organization |     | of     |     |        |       |     |
M. R. Brent. Speech segmentation and word discovery: A computational perspective.
|     |           |               |     |     |       |     |     |     |     |     |     | Trends | in  |
| --- | --------- | ------------- | --- | --- | ----- | --- | --- | --- | --- | --- | --- | ------ | --- |
|     | Sciences, | 3(8):294–301, |     |     | 1999. |     |     |     |     |     |     |        |     |
Cognitive
| V. J. Brown | and | D. S. Tait. |             |     |              |     |        | Species, | volume | 28  | of      |        |     |
| ----------- | --- | ----------- | ----------- | --- | ------------ | --- | ------ | -------- | ------ | --- | ------- | ------ | --- |
|             |     |             | Attentional |     | Set-Shifting |     | Across |          |        |     | Current | Topics | in  |
Neurosciences, pages 363–395. Springer International Publishing, Cham, 2016. ISBN
Behavioral
978-3-319-33913-9. doi: 10.1007/7854_2015_5002. URL https://doi.org/10.1007/7854_
2015_5002.
J. S. Bruner. A Study of Thinking. Routledge, 2nd edition, 1986. doi: 10.4324/9781315083223.
A. P. Burgoyne and R. W. Engle. Attention control: A cornerstone of higher-order cognition.
Current
|            |                  |     | Science, |     | 29(6):624–630, |     | 2020. |     |     |     |     |     |     |
| ---------- | ---------------- | --- | -------- | --- | -------------- | --- | ----- | --- | --- | --- | --- | --- | --- |
| Directions | in Psychological |     |          |     |                |     |       |     |     |     |     |     |     |
T. J. Buschman and E. K. Miller. Goal-direction and top-down control.
|           |         |               |     |           |                     |     |     |     | Philosophical |     | Transactions |     | of  |
| --------- | ------- | ------------- | --- | --------- | ------------------- | --- | --- | --- | ------------- | --- | ------------ | --- | --- |
|           |         |               |     | Sciences, | 369(1655):20130471, |     |     |     | 2014.         |     |              |     |     |
| the Royal | Society | B: Biological |     |           |                     |     |     |     |               |     |              |     |     |
R. B. Cattell. The measurement of adult intelligence. bulletin, 40(3):153, 1943.
Psychological
A. Cheng, A. Jacovi, A. Globerson, B. Golan, C. Kwong, C. Alberti, C. Tao, E. Ben-David, G. S.
Tomar, L. Haas, Y. Bitton, A. Bloniarz, A. Bai, A. Wang, A. Siddiqui, A. B. Castillo, A. Atias, C. Liu,
C. Fry, D. Balle, D. Ghosal, D. Kukliansky, D. Marcus, E. Gribovskaya, E. Ofek, H. Zhuang, I. Laish,
J. Ackermann, L. Wang, M. Risdal, M. Barnes, M. Fink, M. Amin, M. Ambar, N. Potikha, N. Gupta,
N. Katz, N. Velan, O. Roval, O. Ram, P. Zablotskaia, P. Bang, P. Agrawal, R. Ghiya, S. Ganapathy,
S. Baumgartner, S. Erell, S. Prakash, T. Sellam, V. Rao, X. Wang, Y. Akulov, Y. Yang, Z. Yang,
Z. Lai, Z. Wu, A. Dragan, A. Hassidim, F. Pereira, S. Petrov, S. Venkatachary, T. Doshi, Y. Matias,
S. Goldshtein, and D. Das. The facts leaderboard: A comprehensive benchmark for large language
model factuality, 2025. URL https://arxiv.org/abs/2512.10791.
P. W. Cheng and K. J. Holyoak. Pragmatic reasoning schemas. Cognitive Psychology, 17(4):391–416,
1985. ISSN 0010-0285. doi: https://doi.org/10.1016/0010-0285(85)90014-3. URL https:
//www.sciencedirect.com/science/article/pii/0010028585900143.
F. Chollet. On the measure of intelligence. arXiv preprint arXiv:1911.01547, 2019.
F.Chollet,M.Knoop,G.Kamradt,B.Landers,andH.Pinkard. Arc-agi-2: Anewchallengeforfrontier
| ai reasoning | systems. |        | arXiv  | preprint | arXiv:2505.11831, |        |       | 2025. |     |     |     |     |     |
| ------------ | -------- | ------ | ------ | -------- | ----------------- | ------ | ----- | ----- | --- | --- | --- | --- | --- |
| N. Chomsky.  |          |        |        | syntax.  | MIT               | Press, | 1965. |       |     |     |     |     |     |
|              | Aspects  | of the | theory | of       |                   |        |       |       |     |     |     |     |     |
A. Chung and R. N. Rimal. Social norms: a review. Research, 4:1–28, 2016.
|     |     |     |     |     |     |     | Review | of Communication |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | ------ | ---------------- | --- | --- | --- | --- | --- |
ISSN 2255-4165. doi: https://doi.org/10.12840/issn.2255-4165.2016.04.01.008.
24

MeasuringProgressTowardAGI:ACognitiveFramework
N. J. Cohen and L. R. Squire. Preserved learning and retention of pattern-analyzing skill in amnesia:
Dissociation of knowing how and knowing that. Science, 210(4466):207–210, 1980.
G. Comanici, E. Bieber, M. Schaekermann, I. Pasupat, N. Sachdeva, I. Dhillon, M. Blistein, O. Ram,
D.Zhang,E.Rosen,etal. Gemini2.5: Pushingthefrontierwithadvancedreasoning,multimodality,
long context, and next generation agentic capabilities. arXiv preprint arXiv:2507.06261, 2025.
M. A. Conway. Episodic memories. Neuropsychologia, 47(11):2305–2313, 2009.
T. N. Cornsweet. Visual Perception. Academic Press, 1970. ISBN 978-0-12-189750-5.
N. Cowan, E. M. Elliott, J. S. Saults, C. C. Morey, S. Mattox, A. Hismjatullina, and A. R. Conway. On
the capacity of attention: Its estimation and its role in working memory and cognitive aptitudes.
| Cognitive | psychology, | 51(1):42–100, |     | 2005. |     |
| --------- | ----------- | ------------- | --- | ----- | --- |
V. Danthiir, R. D. Roberts, R. Schulze, and O. Wilhelm. Mental speed: On frameworks, paradigms,
and a platform for the future. In O. Wilhelm and R. W. Engle, editors, Handbook of Understanding
and Measuring Intelligence, pages 27–46. Sage Publications, Inc., Thousand Oaks, CA, 2005. doi:
10.4135/9781452233529.n3.
I. Dasgupta, A. K. Lampinen, S. C. Y. Chan, H. R. Sheahan, A. Creswell, D. Kumaran, J. L. McClelland,
and F. Hill. Language models show human-like content effects on reasoning tasks, 2024. URL
https://arxiv.org/abs/2207.07051.
E. H. de Haan and H. C. Dijkerman. Somatosensation in the brain: a theoretical re-evaluation and a
| new model. |        |              | Sciences, | 24(7):529–541, | 2020. |
| ---------- | ------ | ------------ | --------- | -------------- | ----- |
|            | Trends | in Cognitive |           |                |       |
A. Diamond. Executive functions. Annual review of psychology, 64(1):135–168, 2013.
A.DickinsonandB.Balleine. Motivationalcontrolofgoal-directedaction. Animallearning&behavior,
| 22(1):1–18, | 1994. |     |     |     |     |
| ----------- | ----- | --- | --- | --- | --- |
R. L. Diehl, A. J. Lotto, and L. L. Holt. Speech perception. Annu. Rev. Psychol., 55(1):149–179, 2004.
K.Dunbar. Whatscientificthinkingrevealsaboutthenatureofcognition. InK.Crowley,C.D.Schunn,
and T. Okada, editors, Designing for science: Implications from everyday, classroom, and professional
| settings, | pages 115–140. | Lawrence |     | Erlbaum Associates, | 2001. |
| --------- | -------------- | -------- | --- | ------------------- | ----- |
J. Dunlosky and J. Metcalfe. Metacognition. Metacognition. Sage Publications, Inc, Thousand Oaks,
| CA, US, | 2009. ISBN | 978-1-4129-3972-0 |     | (Paperback). |     |
| ------- | ---------- | ----------------- | --- | ------------ | --- |
J. Dunlosky, K. A. Rawson, E. J. Marsh, M. J. Nathan, and D. T. Willingham. Improving students’
learning with effective learning techniques: Promising directions from cognitive and educational
psychology. Psychological Science in the Public interest, 14(1):4–58, 2013.
| R. W. Engle. | Working | memory | capacity | as executive | attention. |
| ------------ | ------- | ------ | -------- | ------------ | ---------- |
Current directions in psychological
| science, | 11(1):19–23, | 2002. |     |     |     |
| -------- | ------------ | ----- | --- | --- | --- |
R. W. Engle. Working memory and executive attention: A revisit. science,
Perspectives on psychological
| 13(2):190–193, | 2018. |     |     |     |     |
| -------------- | ----- | --- | --- | --- | --- |
R. A. Epstein and C. I. Baker. Scene perception in the human brain. Annual review of vision science, 5
| (1):373–397, | 2019. |     |     |     |     |
| ------------ | ----- | --- | --- | --- | --- |
25

MeasuringProgressTowardAGI:ACognitiveFramework
K. A. Ericsson, R. R. Hoffman, A. Kozbelt, and A. M. Williams, editors. The Cambridge Handbook
of Expertise and Expert Performance. Cambridge Handbooks in Psychology. Cambridge University
| Press, | 2 edition, 2018. |     |     |     |     |
| ------ | ---------------- | --- | --- | --- | --- |
M. Esterman and D. Rothlein. Models of sustained attention. Current opinion in psychology, 29:
| 174–180, | 2019. |     |     |     |     |
| -------- | ----- | --- | --- | --- | --- |
M. J. Farah.
Visual agnosia: disorders of object recognition and what they tell us about normal vision.
| The MIT | Press, 1990. |     |     |     |     |
| ------- | ------------ | --- | --- | --- | --- |
G. T. Fechner. psychophysik, volume 2. Breitkopf u. Härtel, 1860.
|     | Elemente | der |     |     |     |
| --- | -------- | --- | --- | --- | --- |
E. Fedorenko, A. Ivanova, R. Dhamala, and M. U. Bers. The language of programming: A
cognitive perspective. Sciences, 23(7):525–528, 2019. ISSN 1364-6613.
|                                                  |     | Trends | in Cognitive |     |     |
| ------------------------------------------------ | --- | ------ | ------------ | --- | --- |
| doi: https://doi.org/10.1016/j.tics.2019.04.010. |     |        |              | URL |     |
https://www.sciencedirect.com/
science/article/pii/S1364661319301020.
J.H.Flavell. Metacognitionandcognitivemonitoring: Anewareaofcognitive–developmentalinquiry.
|     | psychologist, | 34(10):906, | 1979. |     |     |
| --- | ------------- | ----------- | ----- | --- | --- |
American
S. M. Fleming and N. D. Daw. Self-evaluation of decision-making: A general bayesian framework for
| metacognitive | computation. |     |     | review, 124(1):91, | 2017. |
| ------------- | ------------ | --- | --- | ------------------ | ----- |
Psychological
S.M.FlemingandH.C.Lau. Howtomeasuremetacognition. Frontiersinhumanneuroscience,8:443,
2014.
A.D.Friederici. Towardsaneuralbasisofauditorysentenceprocessing. Trendsincognitivesciences,6
| (2):78–84, | 2002. |     |     |     |     |
| ---------- | ----- | --- | --- | --- | --- |
C. Frith and U. Frith. Theory of mind. biology, 15(17):R644–R645, 2005.
Current
J. B. Fritz, M. Elhilali, S. V. David, and S. A. Shamma. Auditory attention—focusing the searchlight
| on sound. |         |         | neurobiology, | 17(4):437–455, | 2007. |
| --------- | ------- | ------- | ------------- | -------------- | ----- |
|           | Current | opinion | in            |                |       |
M. F. Garrett. Processes in language production. In F. J. Newmeyer, editor, Language: Psychological
and biological aspects, pages 69–96. Cambridge University Press, 1988.
K.R.Gegenfurtner. Corticalmechanismsofcolourvision. NatureReviewsNeuroscience,4(7):563–572,
2003.
D. Gentner and F. Maravilla. reasoning, pages 186–203. The Routledge international
Analogical
handbook series. Routledge/Taylor & Francis Group, New York, NY, US, 2018.
S. J. Gershman and Y. Niv. Learning latent structure: carving nature at its joints.
Current opinion in
| neurobiology, | 20(2):251–256, |     | 2010. |     |     |
| ------------- | -------------- | --- | ----- | --- | --- |
A. Gilchrist, C. Kossyfidis, F. Bonato, T. Agostini, J. Cataliotti, X. Li, B. Spehar, V. Annan, and
E.Economou. Ananchoringtheoryoflightnessperception. Psychologicalreview,106(4):795,1999.
C. Gilmore, S. M. Göbel, and M. Inglis. An introduction to mathematical cognition. Routledge, 2018.
S.GinsburgandE.Jablonka. Theevolutionofassociativelearning: Afactorinthecambrianexplosion.
| Journal | of theoretical | biology, | 266(1):11–20, | 2010. |     |
| ------- | -------------- | -------- | ------------- | ----- | --- |
B.GoertzelandC.Pennachin,editors. ArtificialGeneralIntelligence. CognitiveTechnologies.Springer
Berlin, Heidelberg, 2007. ISBN 978-3-540-23733-4. doi: 10.1007/978-3-540-68677-4.
26

MeasuringProgressTowardAGI:ACognitiveFramework
N. D. Goodman, J. B. Tenenbaum, J. Feldman, and T. L. Griffiths. A rational analysis of rule-based
| concept | learning. | Cognitive |     | science, 32(1):108–154, |     | 2008. |     |     |     |
| ------- | --------- | --------- | --- | ----------------------- | --- | ----- | --- | --- | --- |
J. A. Grahn. Neural mechanisms of rhythm perception: current findings and future perspectives.
| Topics | in cognitive | science, | 4(4):585–606, |     | 2012. |     |     |     |     |
| ------ | ------------ | -------- | ------------- | --- | ----- | --- | --- | --- | --- |
A. M. Grant. Rethinking psychological mindedness: Metacognition, self-reflection, and insight.
| Behaviour       | Change,        | 18(1):8–17, |       | 2001.             |          |           |                 |            |              |
| --------------- | -------------- | ----------- | ----- | ----------------- | -------- | --------- | --------------- | ---------- | ------------ |
| M. Gubrud.      | Nanotechnology |             |       | and international |          | security. | In              |            |              |
|                 |                |             |       |                   |          |           | Fifth Foresight | Conference | on Molecular |
| Nanotechnology, |                | Nov.        | 1997. | Presented         | November | 1997.     |                 |            |              |
L. Haas, G. Yona, G. D’Antonio, S. Goldshtein, and D. Das. Simpleqa verified: A reliable factuality
benchmark to measure parametric knowledge. arXiv:2509.07968, 2025.
|     |     |     |     |     |     | arXiv preprint |     |     |     |
| --- | --- | --- | --- | --- | --- | -------------- | --- | --- | --- |
R. N. Haber and M. Hershenson. The psychology of visual perception. Holt, Rinehart & Winston, 1973.
J. Harris and J. Smith. Sensation and perception. SAGE Publications Ltd, 2022.
N. Harvey. Confidence in judgment. sciences, 1(2):78–82, 1997.
|     |     |     |     | Trends | in cognitive |     |     |     |     |
| --- | --- | --- | --- | ------ | ------------ | --- | --- | --- | --- |
E. Heit. Properties of inductive reasoning. Psychonomic bulletin & review, 7(4):569–592, 2000.
D. Hendrycks, D. Song, C. Szegedy, H. Lee, Y. Gal, E. Brynjolfsson, S. Li, A. Zou, L. Levine, B. Han,
J. Fu, Z. Liu, J. Shin, K. Lee, M. Mazeika, L. Phan, G. Ingebretsen, A. Khoja, C. Xie, O. Salaudeen,
M. Hein, K. Zhao, A. Pan, D. Duvenaud, B. Li, S. Omohundro, G. Alfour, M. Tegmark, K. McGrew,
G. Marcus, J. Tallinn, E. Schmidt, and Y. Bengio. A definition of agi. pre-print, 2025.
E. T. Higgins and J. A. Bargh. Social cognition and social perception. Annual review of psychology, 38
| (1):369–425, |     | 1987. |     |     |     |     |     |     |     |
| ------------ | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
A. Hollingworth. Object-position binding in visual memory for natural scenes and object arrays.
|         |                 |     |             |       |            |     | Performance, | 33(1):31, | 2007. |
| ------- | --------------- | --- | ----------- | ----- | ---------- | --- | ------------ | --------- | ----- |
| Journal | of Experimental |     | Psychology: | Human | Perception |     | and          |           |       |
K. J. Holyoak and B. A. Spellman. Thinking. Annual review of psychology, 44(1):265–315, 1993.
A. Jacovi, A. Caciularu, O. Goldman, and Y. Goldberg. Stop uploading test data in plain text:
Practical strategies for mitigating data contamination by evaluation benchmarks. arXiv preprint
| arXiv:2305.10160, |     | 2023. |     |     |     |     |     |     |     |
| ----------------- | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
M. K. Johnson, S. Hashtroudi, and D. S. Lindsay. Source monitoring. Psychological bulletin, 114(1):3,
1993.
P. N. Johnson-Laird. Deductive reasoning. psychology, 50(1):109–135, 1999.
|     |     |     |     |     | Annual | review | of  |     |     |
| --- | --- | --- | --- | --- | ------ | ------ | --- | --- | --- |
J.-H. Jung, P. J. Seo, E. Oh, and J. Kim. Temperature perception by plants. Science, 28
Trends in Plant
| (8):924–940, |     | 2023. |     |     |     |     |     |     |     |
| ------------ | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
F. Katsuki and C. Constantinidis. Bottom-up and top-down attention: different processes and
overlapping neural systems. Neuroscientist, 20(5):509–521, 2014.
The
G. Kaufmann. What to measure? a new look at the concept of creativity. Scandinavian Journal
Research, 47(3):235–251, 2003. doi: 10.1080/00313830308604. URL
| of Educational |     |     |     |     |     |     |     |     | https: |
| -------------- | --- | --- | --- | --- | --- | --- | --- | --- | ------ |
//doi.org/10.1080/00313830308604.
P.Kendeou,K.L.McMaster,andT.J.Christ. Readingcomprehension: Corecomponentsandprocesses.
|        |          |          |            |     | Sciences, | 3(1):62–69, | 2016. |     |     |
| ------ | -------- | -------- | ---------- | --- | --------- | ----------- | ----- | --- | --- |
| Policy | Insights | from the | Behavioral | and | Brain     |             |       |     |     |
27

MeasuringProgressTowardAGI:ACognitiveFramework
P. Kent. Fluid intelligence: A brief history. Applied Neuropsychology: Child, 6(3):193–203, 2017.
D. Klahr. Exploring science: The cognition and development of discovery processes. MIT press, 2000.
K. Kovacs and A. R. Conway. Process overlap theory: A unified account of the general factor of
| intelligence. | Psychological |     | Inquiry, |     | 27(3):151–177, | 2016. |     |     |     |
| ------------- | ------------- | --- | -------- | --- | -------------- | ----- | --- | --- | --- |
A. A. Kumar. Semantic memory: A review of methods, models, and current challenges.
Psychonomic
| bulletin | & review, | 28(1):40–80, |     | 2021. |     |     |     |     |     |
| -------- | --------- | ------------ | --- | ----- | --- | --- | --- | --- | --- |
J. P. Leighton and R. J. Sternberg, editors. Reasoning. Cambridge University Press,
|     |     |     |     |     | The | Nature of |     |     |     |
| --- | --- | --- | --- | --- | --- | --------- | --- | --- | --- |
2003.
A.M.Leslie,O.Friedman,andT.P.German. Coremechanismsin‘theoryofmind’. Trendsincognitive
| sciences, | 8(12):528–533, |     | 2004. |     |     |     |     |     |     |
| --------- | -------------- | --- | ----- | --- | --- | --- | --- | --- | --- |
D. Marr. Vision: A Computational Investigation into the Human Representation and Processing of Visual
| Information.  | Henry        | Holt | and                | Co., Inc., | 1982.      |             |              |                    |        |
| ------------- | ------------ | ---- | ------------------ | ---------- | ---------- | ----------- | ------------ | ------------------ | ------ |
| D. Marr and   | E. Hildreth. |      | Theory             | of edge    | detection. |             |              |                    |        |
|               |              |      |                    |            |            | Proceedings | of the Royal | Society of London. | Series |
| B. Biological | Sciences,    |      | 207(1167):187–217, |            | 1980.      |             |              |                    |        |
F. Martínez-Plumed, R. B. Prudêncio, A. Martínez-Usó, and J. Hernández-Orallo. Item response
theory in ai: Analysing machine learning classifiers at the instance level. Artificial Intelligence,
271:18–42, 2019. ISSN 0004-3702. doi: https://doi.org/10.1016/j.artint.2018.09.004. URL
https://www.sciencedirect.com/science/article/pii/S0004370219300220.
M. G. Mattar and M. Lengyel. Planning in the brain. Neuron, 110(6):914–934, 2022.
R. E. Mayer and M. C. Wittrock. Problem solving. In P. A. Alexander and P. H. Winne, editors,
Psychology, pages 287–303. Lawrence Erlbaum Associates Publishers,
| Handbook | of  | Educational |     |     |     |     |     |     |     |
| -------- | --- | ----------- | --- | --- | --- | --- | --- | --- | --- |
| Mahwah,  | NJ, | 2006.       |     |     |     |     |     |     |     |
M. Mazeika, A. Gatti, C. Menghini, U. M. Sehwag, S. Singhal, Y. Orlovskiy, S. Basart, M. Sharma,
D. Peskoff, E. Lau, J. Lim, L. Carroll, A. Blair, V. Sivakumar, S. Basu, B. Kenstler, Y. Ma, J. Michael,
X. Li, O. Ingebretsen, A. Mehta, J. Mottola, J. Teichmann, K. Yu, Z. Shaik, A. Khoja, R. Ren,
J. Hausenloy, L. Phan, Y. Htet, A. Aich, T. Rabbani, V. Shah, A. Novykov, F. Binder, K. Chugunov,
L. Ramirez, M. Geralnik, H. Mesura, D. Lee, E.-Y. H. Cardona, A. Diamond, S. Yue, A. Wang, B. Liu,
E. Hernandez, and D. Hendrycks. Remote labor index: Measuring ai automation of remote work,
| 2025. | URL https://arxiv.org/abs/2510.26787. |     |     |     |     |     |     |     |     |
| ----- | ------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- |
M.A.McDanielandG.O.Einstein. Anoverviewandsynthesisofanemergingfield.
Prospectivememory:
| Sage Publications, |     | 2007. |     |     |     |     |     |     |     |
| ------------------ | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
J. H. McDermott. The cocktail party problem. Biology, 19(22):R1024–R1027, 2009.
Current
J. Metcalfe. Learning from errors. Annual review of psychology, 68(1):465–489, 2017.
K. J. Mitchell and M. K. Johnson. Source monitoring: Attributing mental experiences. In E. Tulving
and F. I. M. Craik, editors, memory, pages 179–195. Oxford University
|        |       |     |     | The Oxford | handbook | of  |     |     |     |
| ------ | ----- | --- | --- | ---------- | -------- | --- | --- | --- | --- |
| Press, | 2000. |     |     |            |          |     |     |     |     |
A. Miyake, N. P. Friedman, M. J. Emerson, A. H. Witzki, A. Howerter, and T. D. Wager. The unity and
diversity of executive functions and their contributions to complex “frontal lobe” tasks: A latent
| variable | analysis. | Cognitive |     | psychology, | 41(1):49–100, | 2000. |     |     |     |
| -------- | --------- | --------- | --- | ----------- | ------------- | ----- | --- | --- | --- |
28

MeasuringProgressTowardAGI:ACognitiveFramework
J. Morand-Ferron. Why learn? the adaptive value of associative learning in wild populations. Current
| opinion | in behavioral | sciences, |     | 16:73–79, | 2017. |     |     |     |     |     |     |
| ------- | ------------- | --------- | --- | --------- | ----- | --- | --- | --- | --- | --- | --- |
M. R. Morris, J. Sohl-Dickstein, N. Fiedel, T. Warkentin, A. Dafoe, A. Faust, C. Farabet, and S. Legg.
Position: Levels of agi for operationalizing progress on the path to agi. In Forty-first International
| Conference | on Machine |     | Learning, | 2024. |     |     |     |     |     |     |     |
| ---------- | ---------- | --- | --------- | ----- | --- | --- | --- | --- | --- | --- | --- |
M. R. Morris, D. Altman, H. Belfield, A. Goemans, H. Iqbal, R. Burnell, I. Gabriel, S. Albanie, and
A. Dafoe. Characterizing model jaggedness supports safety and usability. Google DeepMind Techni-
cal Report, January 2026. URL https://cs.stanford.edu/~merrie/papers/jaggedness_
preprint.pdf.
T. O. Nelson. Metamemory: A theoretical framework and new findings. In G. H. Bower, editor, The
|            |             |     | Motivation, |     | volume | 26  | of         |     |             | Motivation, | pages |
| ---------- | ----------- | --- | ----------- | --- | ------ | --- | ---------- | --- | ----------- | ----------- | ----- |
| Psychology | of Learning | and |             |     |        |     | Psychology |     | of Learning | and         |       |
125–173. Academic Press, 1990. doi: https://doi.org/10.1016/S0079-7421(08)60053-5. URL
https://www.sciencedirect.com/science/article/pii/S0079742108600535.
N. Nersessian. The cognitive basis of model-based reasoning in science. Science,
|          |                                    |     |     |     |     |     |     |     | The | Cognitive Basis | of  |
| -------- | ---------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --------------- | --- |
| 05 2002. | doi: 10.1017/CBO9780511613517.008. |     |     |     |     |     |     |     |     |                 |     |
K. Nishikawa, A. A. Biewener, P. Aerts, A. N. Ahn, H. J. Chiel, M. A. Daley, T. L. Daniel, R. J. Full,
M. E. Hale, T. L. Hedrick, A. K. Lappin, T. R. Nichols, R. D. Quinn, R. A. Satterlie, and B. Szymik.
Neuromechanics: an integrative approach for understanding motor control.
|     |     |     |     |     |     |     |     |     |     | Integrative | and Com- |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ----------- | -------- |
parative Biology, 47(1):16–54, 05 2007. ISSN 1540-7063. doi: 10.1093/icb/icm024. URL
https://doi.org/10.1093/icb/icm024.
D. Norris. Models of visual word recognition. Trends in cognitive sciences, 17(10):517–524, 2013.
| OpenAI. | Learning | to  | Reason | with | LLMs, | 2024. |     | URL |     |     |     |
| ------- | -------- | --- | ------ | ---- | ----- | ----- | --- | --- | --- | --- | --- |
https://openai.com/index/
learning-to-reason-with-llms/.
A.M.Owen. Cognitiveplanninginhumans: neuropsychological,neuroanatomicalandneuropharma-
| cological | perspectives. |     |          | neurobiology, |     | 53(4):431–450, |     |     | 1997. |     |     |
| --------- | ------------- | --- | -------- | ------------- | --- | -------------- | --- | --- | ----- | --- | --- |
|           |               |     | Progress | in            |     |                |     |     |       |     |     |
A. J. Oxenham. Pitch perception. Journal of Neuroscience, 32(39):13335–13338, 2012.
A. J. Parker. Binocular depth perception and the cerebral cortex. Neuroscience, 8(5):
|          |       |     |     |     |     |     |     |     | Nature Reviews |     |     |
| -------- | ----- | --- | --- | --- | --- | --- | --- | --- | -------------- | --- | --- |
| 379–391, | 2007. |     |     |     |     |     |     |     |                |     |     |
V.Patraucean,L.Smaira,A.Gupta,A.Recasens,L.Markeeva,D.Banarse,S.Koppula,M.Malinowski,
Y. Yang, C. Doersch, et al. Perception test: A diagnostic benchmark for multimodal video models.
|          |           |             |     |            | Systems, |     | 36:42748–42761, |     | 2023. |     |     |
| -------- | --------- | ----------- | --- | ---------- | -------- | --- | --------------- | --- | ----- | --- | --- |
| Advances | in Neural | Information |     | Processing |          |     |                 |     |       |     |     |
T.Patwardhan,R.Dias,E.Proehl,G.Kim,M.Wang,O.Watkins,S.P.Fishman,M.Aljubeh,P.Thacker,
L. Fauconnet, N. S. Kim, P. Chao, S. Miserendino, G. Chabot, D. Li, M. Sharman, A. Barr, A. Glaese,
and J. Tworek. Gdpval: Evaluating ai model performance on real-world economically valuable
| tasks, | 2025. URL | https://arxiv.org/abs/2510.04374. |     |     |     |     |     |     |     |     |     |
| ------ | --------- | --------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
L. Phan, A. Gatti, Z. Han, N. Li, J. Hu, H. Zhang, C. B. C. Zhang, M. Shaaban, J. Ling, S. Shi, et al.
| Humanity’s | last exam. |     | arXiv preprint |     | arXiv:2501.14249, |     |     | 2025. |     |     |     |
| ---------- | ---------- | --- | -------------- | --- | ----------------- | --- | --- | ----- | --- | --- | --- |
M. J. Pickering and S. Garrod. An integrated theory of language production and comprehension.
|            |           | Sciences, |     | 36(4):329–347, |     | 2013. | doi: | 10.1017/S0140525X12001495. |     |     |     |
| ---------- | --------- | --------- | --- | -------------- | --- | ----- | ---- | -------------------------- | --- | --- | --- |
| Behavioral | and Brain |           |     |                |     |       |      |                            |     |     |     |
29

MeasuringProgressTowardAGI:ACognitiveFramework
S. Pinker. The Language Instinct: The New Science of Language and Mind. William Morrow and
| Company, |     | New York, | 1994. | ISBN | 978-0-06-097651-4. |     |     |     |     |     |
| -------- | --- | --------- | ----- | ---- | ------------------ | --- | --- | --- | --- | --- |
D. G. Rand andM. A. Nowak. Human cooperation. sciences, 17(8):413–425, 2013.
|     |     |     |     |     |     | Trends incognitive |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ------------------ | --- | --- | --- | --- |
M. G. Rhodes. Judgments of learning: Methods, data, and theory. In J. Dunlosky and S. K. Tauber,
editors, Metamemory, pages 65–80. Oxford University Press, 06 2016.
|     | The | Oxford | Handbook |     | of  |     |     |     |     |     |
| --- | --- | ------ | -------- | --- | --- | --- | --- | --- | --- | --- |
ISBN 9780199336746. doi: 10.1093/oxfordhb/9780199336746.013.4. URL https://doi.org/
10.1093/oxfordhb/9780199336746.013.4.
M. Riesenhuber and T. Poggio. Models of object recognition. neuroscience, 3(11):1199–1204,
Nature
2000.
| L. J. Rips. | Reasoning. |     |        |        | psychology, | 41:321–353, | 1990. |     |     |     |
| ----------- | ---------- | --- | ------ | ------ | ----------- | ----------- | ----- | --- | --- | --- |
|             |            |     | Annual | review | of          |             |       |     |     |     |
D.Romero-Alvarado,F.Martínez-Plumed,L.Pacchiardi,H.Save,S.M.Pawar,B.Mehrbakhsh,P.A.M.
Casares, B. Slater, P. Bova, P. Romero, Z. R. Tidler, J. Prunty, L. Sun, and J. Hernandez-Orallo.
Capabilities ain’t all you need: Measuring propensities in ai, 2026. URL https://arxiv.org/
abs/2602.18182.
J. R. Saffran. Statistical language learning: Mechanisms and constraints.
|               |     |          |                |     |       |     |     |     | Current | directions in |
| ------------- | --- | -------- | -------------- | --- | ----- | --- | --- | --- | ------- | ------------- |
| psychological |     | science, | 12(4):110–114, |     | 2003. |     |     |     |         |               |
M. Sarter, B. Givens, and J. P. Bruno. The cognitive neuroscience of sustained attention: where
| top-down |     | meets | bottom-up. |       |          | reviews, 35(2):146–160, |     | 2001. |     |     |
| -------- | --- | ----- | ---------- | ----- | -------- | ----------------------- | --- | ----- | --- | --- |
|          |     |       |            | Brain | research |                         |     |       |     |     |
A. Schoenfeld. Mathematical Problem Solving. Academic Press, 1985. ISBN 9780126288711.
D.R.Shanks.Thepsychologyofassociativelearning,volume13.CambridgeUniversityPressCambridge,
1995.
A.ShinandK.Kaneko. Largelanguagemodelslackunderstandingofcharactercompositionofwords.
| arXiv | preprint | arXiv:2405.11357, |     |     | 2024. |     |     |     |     |     |
| ----- | -------- | ----------------- | --- | --- | ----- | --- | --- | --- | --- | --- |
B. F. Skinner. Operant behavior. psychologist, 18(8):503, 1963.
American
M. W. Smith, J. Sharit, and S. J. Czaja. Aging, motor control, and the performance of computer
mouse tasks. Factors, 41(3):389–396, 1999. doi: 10.1518/001872099779611102. URL
Human
https://doi.org/10.1518/001872099779611102.
L. K. Son and B. L. Schwartz. The relation between metacognitive monitoring and control. In T. J.
Perfect and B. L. Schwartz, editors, metacognition, pages 15–38. Cambridge University
Applied
| Press, | 2002. |     |     |     |     |     |     |     |     |     |
| ------ | ----- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
S.A.Spence,M.D.Hunter,T.F.D.Farrow,R.D.Green,D.H.Leung,C.J.Hughes,andV.Ganesan. A
cognitive neurobiological account of deception: evidence from functional neuroimaging.
Philosoph-
ical Transactions of the Royal Society of London. Series B, Biological Sciences, 359(1451):1755–1762,
| 2004. | doi: | 10.1098/rstb.2004.1555. |     |     |     |     |     |     |     |     |
| ----- | ---- | ----------------------- | --- | --- | --- | --- | --- | --- | --- | --- |
L. R. Squire and E. R. Kandel. Memory : from mind to molecules. Scientific American Library series ;
no. 69. Scientific American Library, New York, 1999. ISBN 0716750716.
R. J. Stainton, editor. Science. Wiley-Blackwell, Oxford, 2006.
|                 |     |            | Contemporary  |       | Debates     | in Cognitive   |           |     |            |            |
| --------------- | --- | ---------- | ------------- | ----- | ----------- | -------------- | --------- | --- | ---------- | ---------- |
| R. J. Sternberg |     | and        | T. I. Lubart. |       |             |                |           |     | Paradigms, | page 3–15. |
|                 |     |            |               |       | The Concept | of Creativity: | Prospects | and |            |            |
| Cambridge       |     | University | Press,        | 1998. |             |                |           |     |            |            |
30

MeasuringProgressTowardAGI:ACognitiveFramework
R. J. Stevenson. An initial evaluation of the functions of human olfaction. Chemical Senses, 35(1):
3–20, 11 2009. ISSN 0379-864X. doi: 10.1093/chemse/bjp083. URL https://doi.org/10.
1093/chemse/bjp083.
| E. Styles. | The psychology | of attention. | Psychology |     | Press, 2006. |     |     |     |
| ---------- | -------------- | ------------- | ---------- | --- | ------------ | --- | --- | --- |
R. S. Sutton, A. G. Barto, et al. introduction, volume 1. MIT press
|            |       |     | Reinforcement |     | learning: | An  |     |     |
| ---------- | ----- | --- | ------------- | --- | --------- | --- | --- | --- |
| Cambridge, | 1998. |     |               |     |           |     |     |     |
H. Tajfel. Social perception. In G. Humphrey and M. Argyle, editors, Social Psychology Through
| Experiment, | chapter | 1, pages 20–54. | Methuen, |     | London, | 1962. |     |     |
| ----------- | ------- | --------------- | -------- | --- | ------- | ----- | --- | --- |
P. Tarricone. The taxonomy of metacognition. Psychology press, 2011.
A. Taubenfeld, Z. Gekhman, L. Nezry, O. Feldman, N. Harris, S. Reddy, R. Stella, A. Goldstein,
M. Croak, Y. Matias, and A. Feder. Evaluating alignment of behavioral dispositions in llms, 2026.
URL https://arxiv.org/abs/2602.11328.
J. B. Tenenbaum, C. Kemp, T. L. Griffiths, and N. D. Goodman. How to grow a mind: Statistics,
| structure, | and abstraction. | science, | 331(6022):1279–1285, |     |     | 2011. |     |     |
| ---------- | ---------------- | -------- | -------------------- | --- | --- | ----- | --- | --- |
J. Theeuwes. Exogenous and endogenous control of attention: The effect of visual onsets and offsets.
|            | psychophysics, | 49(1):83–90, |     | 1991. |     |     |     |     |
| ---------- | -------------- | ------------ | --- | ----- | --- | --- | --- | --- |
| Perception | &              |              |     |       |     |     |     |     |
J. T. Todd. The visual perception of 3d shape. Trends in cognitive sciences, 8(3):115–121, 2004.
M. J. Traxler and M. A. Gernsbacher, editors. Psycholinguistics. Academic Press, London,
|     |     |     |     | Handbook | of  |     |     |     |
| --- | --- | --- | --- | -------- | --- | --- | --- | --- |
2 edition, 2006. ISBN 978-0-12-369374-7. doi: 10.1016/B978-0-12-369374-7.X5000-7.
A. M. Treisman. Strategies and models of selective attention. review, 76(3):282, 1969.
Psychological
L. M. Trick and Z. W. Pylyshyn. Why are small and large numbers enumerated differently? a
limited-capacity preattentive stage in vision. Review, 101(1):80–102, 1994. doi:
Psychological
10.1037/0033-295X.101.1.80.
E.Tulvingetal. Episodicandsemanticmemory. InOrganizationofmemory,pages381–403.Academic
| Press, 1972. |     |     |     |     |     |     |     |     |
| ------------ | --- | --- | --- | --- | --- | --- | --- | --- |
S. Ullman. High-Level Vision: Object Recognition and Visual Cognition. The MIT Press, 07 1996. ISBN
9780262285353. doi: 10.7551/mitpress/3496.001.0001. URL https://doi.org/10.7551/
mitpress/3496.001.0001.
D.VanMoorselaarandH.A.Slagter. Inhibitioninselectiveattention. AnnalsoftheNewYorkAcademy
| Sciences, | 1464(1):204–221, |     | 2020. |     |     |     |     |     |
| --------- | ---------------- | --- | ----- | --- | --- | --- | --- | --- |
of
S. Vazire and E. N. Carlson. Self-knowledge of personality: Do people know themselves? Social and
| personality | psychology | compass, | 4(8):605–620, |     | 2010. |     |     |     |
| ----------- | ---------- | -------- | ------------- | --- | ----- | --- | --- | --- |
V.v.VeenandC.S.Carter.Conflictandcognitivecontrolinthebrain.CurrentDirectionsinPsychological
| Science, | 15(5):237–240, | 2006. |     |     |     |     |     |     |
| -------- | -------------- | ----- | --- | --- | --- | --- | --- | --- |
J.X.Wang. Meta-learninginnaturalandartificialintelligence. CurrentOpinioninBehavioralSciences,
| 38:90–95,     | 2021.              |             |        |     |          |         |            |                   |
| ------------- | ------------------ | ----------- | ------ | --- | -------- | ------- | ---------- | ----------------- |
| R. M. Warren. |                    | Perception, | volume | 109 | of       |         |            | Series. Pergamon, |
|               | Auditory           |             |        |     | Pergamon | General | Psychology |                   |
| 1982. ISBN    | 978-0-08-025957-4. |             |        |     |          |         |            |                   |
31

MeasuringProgressTowardAGI:ACognitiveFramework
D. B. Willingham, M. J. Nissen, and P. Bullemer. On the development of procedural knowledge.
Journal of experimental psychology: learning, memory, and cognition, 15(6):1047, 1989.
W. Wood. Attitude change: Persuasion and social influence. psychology, 51(1):
|          |       |     |     | Annual review | of  |     |
| -------- | ----- | --- | --- | ------------- | --- | --- |
| 539–570, | 2000. |     |     |               |     |     |
E. Yee, E. G. Chrysikou, and S. L. Thompson-Schill. Semantic memory. In
|         |                         |        |         |                   | The Oxford      | Hand- |
| ------- | ----------------------- | ------ | ------- | ----------------- | --------------- | ----- |
|         |                         |        | Topics. | Oxford University | Press, 12 2013. | ISBN  |
| book of | Cognitive Neuroscience, | Volume | 1: Core |                   |                 |       |
9780199988693. doi: 10.1093/oxfordhb/9780199988693.013.0017. URL https://doi.org/
10.1093/oxfordhb/9780199988693.013.0017.
B. T. Yeo, F. M. Krienen, J. Sepulcre, M. R. Sabuncu, D. Lashkari, M. Hollinshead, J. L. Roffman, J. W.
Smoller,L.Zöllei,J.R.Polimeni,etal. Theorganizationofthehumancerebralcortexestimatedby
| intrinsic | functional connectivity. |         | neurophysiology, | 2011. |     |     |
| --------- | ------------------------ | ------- | ---------------- | ----- | --- | --- |
|           |                          | Journal | of               |       |     |     |
N. Yeung and C. Summerfield. Metacognition in human decision-making: confidence and error
monitoring. Philosophical Transactions of the Royal Society B: Biological Sciences, 367(1594):1310–
1321, 2012.
J.M.Zacks,N.K.Speer,K.M.Swallow,andC.J.Maley. Thebrain’scutting-roomfloor: Segmentation
| of narrative | cinema. Frontiers | in human | neuroscience, | 4:168, 2010. |     |     |
| ------------ | ----------------- | -------- | ------------- | ------------ | --- | --- |
S. Zmigrod and B. Hommel. Feature integration across multimodal perception and action: a review.
| Multisensory | research, 26(1-2):143–157, |     | 2013. |     |     |     |
| ------------ | -------------------------- | --- | ----- | --- | --- | --- |
32