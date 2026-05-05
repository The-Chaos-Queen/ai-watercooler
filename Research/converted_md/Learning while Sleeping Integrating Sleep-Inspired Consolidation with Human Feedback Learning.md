![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-0-0.png)
## **Learning while Sleeping: Integrating Sleep-Inspired** **Consolidation with Human Feedback Learning.**

### TARAKLI, Imene and DI NUOVO, Alessandro <http://orcid.org/0000-0003- 2677-2650> Available from Sheffield Hallam University Research Archive (SHURA) at: https://shura.shu.ac.uk/33782/

This document is the Accepted Version [AM]


**Citation:**


TARAKLI, Imene and DI NUOVO, Alessandro (2024). Learning while Sleeping:
Integrating Sleep-Inspired Consolidation with Human Feedback Learning. In: 2024
IEEE International Conference on Development and Learning (ICDL). IEEE. [Book
Section]


**Copyright and re-use policy**


[See http://shura.shu.ac.uk/information.html](http://shura.shu.ac.uk/information.html)


**Sheffield Hallam University Research Archive**

[http://shura.shu.ac.uk](http://shura.shu.ac.uk/)


# Learning while Sleeping: Integrating Sleep-Inspired Consolidation with Human Feedback Learning



Imene Tarakli
_Sheffield_ _Hallam_ _University_
Sheffield, United Kingdom
i.tarakli@shu.ac.uk


_**Abstract**_ **—Sleep** **plays** **a** **vital** **role** **in** **developmental** **learning.**
**It** **allows** **the** **brain** **to** **consolidate** **daily** **learning** **experiences** **by**
**replaying** **the** **memories** **accumulated** **throughout** **the** **day.** **In** **this**
**work,** **we** **take** **inspiration** **from** **sleep** **and** **propose** **the** **Inverse**
**Forward** **Offline** **Reinforcement** **Model** **(INFORM),** **a** **scalable**
**framework** **that** **first** **learns** **a** **set** **of** **behaviours** **from** **human**
**evaluative** **feedback,** **then** **consolidates** **the** **learning** **by** **applying**
**an** **offline** **inverse** **reinforcement** **learning** **to** **the** **memorised**
**trajectories.** **Experimental** **results** **demonstrate** **that** **INFORM** **is**
**a** **feedback-efficient** **method** **that** **effectively** **learns** **an** **optimal**
**policy** **that** **aligns** **with** **the** **intended** **behaviour** **of** **the** **human.** **A**
**comparative** **analysis** **shows** **that** **the** **learnt** **policies** **are** **robust** **to**
**dynamic** **changes** **in** **the** **environment** **and** **the** **recovered** **rewards**
**allow the robot to be autonomous in its learning. Project website:**
**https://sites.google.com/view/inform-framework**
_**Index**_ _**Terms**_ **—Developmental** **Robotics,** **Cognitive** **Robotics,**
**Interactive** **Agents**


I. INTRODUCTION


From the joyous cheers greeting a baby’s first steps to the
reprimand following a misconduct, or the beaming pride after
an achievement, humans are consistently exposed to evaluative
feedback throughout their lives. This feedback is fundamental
for learning, as it helps individuals acquire new skills, make
informed decisions, and adapt to changes in the environment

[1].
Transferring this ability to learn from evaluative feedback to
robots is a natural transition toward smoother Human-Robot
Interaction (HRI). By emulating natural human interaction,
the teaching process becomes more intuitive and effective,
enabling individuals to guide robots using feedback in the
same manner they would with their peers. As the feedback
precisely tailors the robot’s learning, it allows users to easily
personalise the robot’s behaviour to their desired preferences
without needing specific technical skills.
Several studies investigated how to include human feedback
within the decision-making process of a robot, framing this
approach as Interactive Reinforcement Learning (RL). This


This project has received funding from the European Union’s Horizon 2020
research and innovation programme under the Marie Skłodowska-Curie grant
agreement No 955778.



Alessandro Di Nuovo
_Sheffield_ _Hallam_ _University_
Sheffield, United Kingdom
a.dinuovo@shu.ac.uk


framework has proven effective in various real-world applications, enabling users to shape the behaviour of robots by
providing feedback on each action of the robots. However,
humans do not consider evaluative feedback as a reinforcement
per se, but as a means to communicate the correctness of an
action, often favouring positive over negative feedback [2], [3].
This way of teaching creates positive-reward cycles – the agent
will repeatedly visit the same states to maximise the long-term
reward. Consequently, Interactive RL tends to focus on myopic
learning - the robot privileges immediate rewards over future
ones when making decisions. While this approach accelerates
learning by reducing the time spent exploring future rewards,
it can limit the robot’s understanding of the broader goal of
the task, potentially affecting the generalisation and robustness
of its performance [4].
In contrast, humans effectively learn from evaluative feedback and are capable of generalising and transferring the
knowledge to more complex tasks. However, this learning is
not straightforward. Humans do not acquire robust decisionmaking skills directly from evaluative feedback; it involves
various steps, with sleep playing a crucial role [5]. Indeed,
studies revealed that deep sleep enhances learning by enabling
the consolidation and generalisation of knowledge [6]. Newly
acquired skills are initially stored in the short-term memory
within the hippocampus. During sleep, these memories are
processed and replayed, training additional neurons in the
cortex. This process maximises the information extraction
from each episode and stores it in the brain’s long-term
memory, facilitating the generalisation of learning [7].
Moreover, humans do not solely rely on human feedback
when learning. they infer the goal and intent of the teacher
based on that feedback and internalise the reward to enable
further learning on their own [8].
In this paper, we introduce **IN** verse **F** orward **O** ffline
**R** einforcement **M** odel (INFORM), a model for learning from
evaluative feedback that closely emulates how humans learn.
INFORM initially learns from evaluative feedback by using
a myopic forward interactive RL to predict the teacher’s
preferred actions, storing all trajectories in a replay buffer.
It then initiates a “sleep phase” by replaying these learning


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-2-1.png)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-2-0.png)











Fig. 1: Illustration of the framework. (1) The agent first learns a low-level policy with a myopic interactive RL. All trajectories
of the interaction are stored in a buffer. (2) An offline inverse RL is then applied to the stored trajectories to recover a reward
and a policy that better encodes the high-level information of the task.



experiences in an offline mode. During this phase, Inverse RL
is applied with a high discount factor, allowing the model to
internalise the dynamics of the environment and thus learn a
robust policy and reward function from past experiences [9].
Our contribution can be summarised as follows:

_•_ We introduce INFORM, a framework that combines interactive and inverse RL to enable scalable learning from
human feedback.

_•_ We report that INFORM is the first successful instance
of learning a non-myopic policy from human feedback in
a model-free setting for discrete and continuous environments.

_•_ We empirically prove that INFORM is robust to the
change of dynamics and distributional shifts in a diverse
set of environments.

_•_ We show that the reward function recovered by INFORM
effectively captures the high-level goal of the task, enabling autonomous learning.


II. PRELIMINARIES

In this section, we review the relevant definition and
notations that are used in the rest of this work.


**Reinforcement** **Learning.** RL is a subset of machine
learning that aims to solve problems modeled as Markov
Decision Processes (MDPs) [10]. An MDP is defined as a
tuple _<_ _S, A, T, R, γ_ _>_ where _S_ and _A_ are respectively the
set of possible states and actions; _T_ : _S_ _×_ _A_ _→_ _S_ is the
transition function that gives the probability of transitioning to
another state given the actual state and action; _R_ : _S ×_ _A →_ R
is the reward function which defines the received reward
when performing an action in a state, and _γ_ _∈_ [0 _,_ 1] is the
discount factor that determines the sensitivity of the agent to
future decisions. RL aims to learn policies _π_ : _S_ _→_ _A_ that
improve the discounted sum of returns over time. The return
of each _< s, a >_ pair is given by the action-value defined as:
_Q_ ( _s, a_ ) = _Eπ_ [ [�] _[∞]_ _t_ =0 _[γ][t][R]_ [(] _[s, a]_ [)]][.] [Policies] [that] [maximise] [the]
returns rewards are called optimal and are denoted by _π_ _[∗]_ .


**Inverse** **Reinforcement** **Learning** . In IRL, the problem
is modeled as an MDP/R tuple - MDP without any reward



function _R_ [11]. Instead, we are given a set of trajectories
_D_ = _{_ ( _s_ 1 _, a_ 1) _, ...,_ ( _sn, an_ ) _}_ that are assumed to be samples
from an expert policy _πE_ . The goal is to find a reward
function R that would make the agent reproduce the same
behaviour as the expert.


**Myopic learning** . It occurs when an agent prioritises immediate rewards without considering the long-term consequences
of its actions. This approach may lead to suboptimal performance in complex environments as the agent may not account
for the potential future rewards or penalties. In RL, a learning
approach is considered myopic if it uses a low discount factor
(typically, _γ_ _<_ = 0 _._ 9) [4].


III. RELATED WORKS


**Learning** **from** **human** **evaluative** **feedback.** In interactive
RL, an agent improves its policy based on the scalar feedback
provided by a human teacher. This feedback, interpreted as either a value [12]–[14] or advantage function [15], [16], is nonstationary and inconsistent, making it distinct from standard
environmental rewards. Studies found that humans provide
more positive than negative feedback, resulting in positivereward cycles [2]–[4]. This is addressed by myopic learning;
however, this approach makes the learning less generalisable.
To address this, Knox et al. [4] developed VI-TAMER, a nonmyopic model that merges TAMER with a Value-Iteration
algorithm for robust learning. While this framework improved
the generalisation of the performance, it can only be used in
discrete environments with a known transition model, limiting
its broader applicability.
**Sleep** **Inspired** **Reinforcement** **Learning** Massi et al. [17]
proposed a neuroscience-inspired RL model incorporating a
hippocampal replay mechanism, which demonstrated faster
and more efficient learning through a replay buffer developed
based on neuroscience knowledge about the hippocampus.
Similarly, Tirumala et all. [18] proposed Replay across Experiments (RaE), a framework that reutilises experiences from past
experiments, enhancing exploration and accelerating learning
by replaying diverse trajectories. While these studies showcase
the value of hippocampal-inspired offline learning, they focus
on scenarios with well-defined reward functions. Our research,


in contrast, focuses on learning derived from human feedback,
exploring a new aspect of consolidation learning.


IV. THE INFORM FRAMEWORK


In this section, we present the INverse Forward Offline
Reinforcement Model (INFORM), a framework that scalably
learns generalised policies and reward functions from human
feedback. As depicted in Fig. 1, the model consists of two
phases :


(1) **A** **Forward** **model:** In this initial phase, we use a
myopic interactive RL based on human feedback to train
a preliminary, low-level policy.
(2) **An** **Offline** **Inverse** **model:** Subsequently, we revisit all
the trajectories generated by the previous phase and apply
a non-myopic offline IRL to derive a policy and reward
function that more accurately captures the task’s highlevel objectives.


_A._ _The_ _Forward_ _Model_


The forward model allows a human trainer to tailor the
policy of a robot to a specific behaviour. Initially, the robot
follows a random policy. The human then provides binary
feedback, denoted as f, to assess the correctness of each
_<_ state _,_ action _>_ pair, and guide the policy update H of the
robot toward the desired behaviour by optimising the learning
objective:


2
_L_ ( _θH_ ) = E( _s,a,H_ ) _∼D_ _H_ ˆ ( _s, a_ ; _θH_ ) _−_ _H_ ( _s, a_ ) (1)
��� ���


During this phase, we use the TAMER model, a widely used
framework that effectively learns from evaluative feedback

[12].
At the end of each episode, the robot assesses the success
of its performance based on the environmental return, which
is derived from observations rather than the traditional reward
function. It then stores the trajectories with a success or failure
tag in a replay buffer for use in the next phase.


_B._ _The_ _Offline_ _Inverse_ _Model_


Although the forward model efficiently learns the intended
behaviour of humans from evaluative feedback, the resulting
policy might not generalise well due to the short-slightness of
fully myopic learning with a high discount factor ( _γ_ = 0). In
this setting, the robot only cares about immediate actions and
relies entirely on human feedback which results in immediate,
short-term learning that can limit the robot’s understanding of
the environment and the task.
To overcome this limitation, we propose to emulate the sleep
phase which allows the brain to consolidate the learning by
sorting and reinforcing newly encoded memories and transition
them into the more abstract, generalised type of memory by
training additional neural network [19].
This mechanism is built in the same way as inverse RL, in
which policies are derived from given trajectories. Specifically,
we take an interest in IQ-learn [9], a dynamic-aware imitation
learning model that effectively learns a Q-function from a few



demonstrations and uses it to derive both a policy and a reward
function. While successful results were obtained in different
environments, the method relies on expert demonstrations
and, in more intricate continuous environments, necessitates
direct interaction to capture dynamic information about the
environments.
However, sleep occurs offline without access to optimal
expert trajectories. To align inverse learning with this process,
we modify the IQ-learn objective function to learn from
successful trajectories of the forward model rather than expert
ones. Additionally, we substitute online interaction with the
environment, with samples from the replay buffer of the first
phase, regrouping both successful and unsuccessful trajectories.


max _[∗]_ [(] _[s][′]_ [)]]
_Q∈_ Ω _[J][ ∗]_ [(] _[Q]_ [) =] _[ −]_ [E][(] _[s,a,s][′]_ [)] _[∼]_ [success][ [] _[Q]_ [(] _[s, a]_ [)] _[ −]_ _[γV]_

_−_ E( _s,a,s′_ ) _∼_ replay [ _V_ _[π]_ ( _s_ ) _−_ _γV_ _[π]_ ( _s_ _[′]_ )] (2)

with _V_ _[∗]_ ( _s_ ) = log [�] _a_ [exp] _[ Q]_ [(] _[s, a]_ [)][.]
From the learnt policy, a reward function, encoding the highlevel goal of the task and enabling autonomous learning, can
be recovered as follows:


_r_ ( _s, a, s_ _[′]_ ) = _Q_ ( _s, a_ ) _−_ _γV_ _[π]_ ( _s_ _[′]_ ) (3)


**Algorithm** **1** Pseudocode of the INFORM Framework


**===** **Forward** **Model** **===**
1: Initialise parameters of _Hθ_, _πϕ_, and a replay buffer _D_
2: **for** each episode **do**
3: Initialize a temporary buffer _T_
4: **for** each step **do**

5: _s ←_ observation
6: Select action _a_ :

(Q-learning) _a_ = _argmax_ ( _Hθ_ ( _s_ ))
(actor-critic) _a_ = _π_ ( _· | st_ ; _ϕ_ )
7: _s_ _[′]_ _←_ executing a
8: _h ←_ human feedback

9: Store in temporary buffer _T_ _←T_ _∪_ ( _s, a, s_ _[′]_ _, h_ )
10: Perform a gradient step for _θH_ using Equation 1
11: (only with actor-critic) Perform a gradient step for _ϕπ_
using the following equation:

_L_ ( _ϕπ_ ) = E( _s,a,π_ ) _∼D_ [ _H_ ( _s, a_ ) _−_ log _π_ ( _a|s_ ; _ϕ_ )]
12: **end** **for**
13: Assess success of trajectories _▷success ∈{_ 0 or 1 _}_
14: Store labeled trajectories in replay buffer _D_ _←D_ _∪_
( _T, success_ )
15: **end** **for**

**===** **Inverse** **Model** **===**

16: Initialise parameters of _Qθ_ and optionally _πϕ_
17: **for** each step **do**
18: Get batch from replay buffer _∼D_ [( _s, a, s_ _[′]_ _, success_ )]
19: Perform a gradient step for _θQ_ using Equation 2
20: (only with actor-critic) Perform a gradient step for _ϕπ_
21: **end** **for**
22: Recover reward function using Equation 3


![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-4-0.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-4-1.png)

(a) Gridworld (b) Pusher


Fig. 2: Griwrold and Pusher-V4 environments are used to
assess the performance of INFORM.


V. METHODOLOGY


We structure our methodology to address the following
research questions:


_•_ Can INFORM effectively learn a high-level policy from
past experiences?

_•_ How robust is the consolidated policy learned by INFORM?

_•_ Is the reward function retrieved by INFORM in alignment
with the teacher’s intended outcomes?


_A._ _Environments_


We evaluate INFORM in two distinct scenarios: a discrete
task and a continuous task.
In the discrete setting, we employ the 30-cell gridworld
maze (Figure 2a) from [4]. The agent’s objective is to navigate
from the ’S’ cell to the ’G’ cell in as few steps as possible,
choosing from four directional actions: up, down, left, or right.
A trajectory is deemed successful if the goal is reached in
under 30 steps. This environment, while straightforward, provides a comprehensive platform for a detailed and observable
evaluation of our framework.
For the continuous task, we use the Pusher-V4 task from
Mujoco Gymnasium [20], where a robotic arm with multiple
joints aims to move a cylinder to a target position using its
end effector (Figure 2b). In this environment, a trajectory is
considered as successful if the cylinder is within 0.08 units
from the target position. The increased complexity of this task,
compared to the gridworld maze, enables a more thorough
assessment of the performance of INFORM in complex scenarios.


_B._ _Simulated_ _Feedback_


This study aims to enhance learning from evaluative feedback, not through direct improvements from the feedback, but
by consolidating knowledge derived from human interactions.
For the direct learning from evaluative feedback, we apply
established models that have been previously validated with
human participants [12]. Therefore, to simplify the experimental process and reduce reliance on human feedback, we
implement an oracle to simulate evaluative feedback, facilitating a comprehensive assessment of the INFORM framework.
Similar to Zhang et al. [21], we use a fully trained model as
the oracle. For each given state, s, the learning agent selects



an action, a, based on its current policy while the oracle
simultaneously selects an action, a*, based on its optimal
policy. The oracle is then used to calculate the state-action
value for both actions. When the learning agent’s action
produces a Q-value close to Q(s,a*), t it is considered a
successful action, leading to positive feedback. In cases where
Q-values significantly differ, no feedback is given. This design
aims to replicate the positive feedback bias observed in human
interactions [22].



_F_ ( _s, a_ ) =




+1 if _Q_ ( _s, a_ ) _≥_ _αQ_ ( _s, a_ _[∗]_ )
(4)
0 otherwise



where _α_ is a variable that increases over time to modelize
the diminishing return of human evaluative feedback.


_C._ _Implementation_


In our implementation of INFORM, we use a Deep QNetwork (DQN) [23] for the discrete gridworld environment
and a Soft Actor-Critic (SAC) [24] for the continuous task. We
adapted the CleanRL codebase [25] to align with Algorithm 1,
and selected hyperparameters based on the recommendations
of Garg et al. [9]. Detailed implementation specifics are
available on the project’s website.


VI. RESULTS & DISCUSSION


_A._ _Consolidating_ _learning_ _from_ _human_ _feedback_


We assessed whether INFORM could effectively consolidate
learning from human feedback by developing a non-myopic,
high-level offline policy from previous experiences, without
additional interaction with the environment.
We evaluated the framework on the two environments:
gridworld and Pusher-V4. For both tasks, we first learnt a lowlevel policy from the oracle feedback using TAMER. INFORM
then consolidated the myopic learning by applying offline
inverse RL to the past trajectories with a high-discount factor.
Figure 5 shows the obtained results. INFORM (orange line)
rapidly aligns with the performance of TAMER, representing
the myopic policy derived from human feedback (blue line),
and matches the expert performance (dashed line).
This demonstrates that the learning objective of INFORM
successfully integrates learning from both successful and unsuccessful trajectories to consolidate knowledge by learning a
high-level policy for each task.


_B._ _Robustness_ _to_ _dynamic_ _changes_


We assessed whether the high-level policy obtained with
INFORM is robust against changes in environmental dynamics.
Following the methodology of Eysenbach et al. [26], we
modified the Pusher-v4 task by introducing an obstacle along
the perpendicular bisector between the puck’s initial position and the goal. This obstacle comprises three axis-aligned
blocks, each 3 cm wide, located at (0.32, -0.2), (0.35, -0.23),
and (0.38, -0.26). The modified environment is illustrated in
figure 4b.


Perturbed dynamics


0.2 0.3 0.4 0.5
X Position



Perturbed dynamics


0.20


0.15


0.10


0.05


0.00
TAMER INFORM


(b)



Gridworld (n=5)



Pusher-V4 (n=3)



Original dynamics


0.2 0.3 0.4 0.5
X Position



200


175


150


125


100


75


50


25



~~TAMER, = 0~~





20


40


60


80


100


120


140


160





![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-0.png)






|Col1|Col2|Col3|Col4|Col5|Exp|ert|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
||||||||||
||||||||||
||||||||||
||||||||||



0 20000 40000 60000 80000 100000 120000 140000
Env steps


(a) Gridworld



0 20000 40000 60000 80000 100000
Env steps


(b) Pusher



0.05


0.00


0.05


0.10


0.15


0.20


0.25


0.30


0.35



Fig. 3: Evaluation of INFORM and TAMER across discrete
and continuous Tasks. The expert performance (green dashed
line) sets the target for each environment. Higher values
indicate superior performance in Pusher, while lower values
are better in Gridworld. INFORM effectively recovers nonmyopic policies, matching TAMER’s performance.


(a) (b)


Fig. 4: Perturbation in environmental dynamics. (a) A wall is
added in Gridworld to block the optimal path. (b) The optimal
trjaectory is obstructed with an obstacle.


We initially trained TAMER and INFORM in the original
environment and then tested them in the environment with
altered dynamics over 100 episodes each, for three runs. To
ensure consistency, the same initial state was used in all
episodes. The robustness of each model was evaluated based
on the distance between the final position of the object and
the target’s position.


Figure 5b depicts the success rate of both models in the
original and perturbed dynamics. We notice the high-level
policy obtained with INFORM significantly moves the object
to its target closer than the low-level policy obtained with
TAMER, _p_ _<_ 0 _._ 0001, despite the presence of the obstacle.
As observed in figure 5a, the policy obtained with INFORM
is more likely to go around the obstacles and reach the goal
than TAMER. We posit that the high discount factor enables
the model a more accurate representation of the dynamics of
the environment, which can contribute to the robustness of
the model. In contrast, a myopic policy, primarily oriented
towards the optimal trajectories, may underperform when
deviating from these trajectories. However, it’s important to
acknowledge that despite INFORM’s robust policy, there was
significant variance in performance across various seeds. This
variability suggests that INFORM could be further improved
to enhance the consistency of the results.



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-1.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-2.png)

(a)



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-3.png)

Fig. 5: Robustness evaluation. (a) Comparison of TAMER
and INFORM trajectories on both original and perturbed
environments. (b) Comparison of distance from target over
3 runs. INFORM significantly moves the object closer to the
goal compared to TAMER, learning a high-level policy that
more effectively navigates around obstacles.


_C._ _Reward_ _evaluation_


In this experiment, we aimed to evaluate the reward function
recovered through INFORM. For that, we modified the training
environment to render the policy learned with human feedback
suboptimal. This modification ensures that the reward function
recovered by INFORM captures the high-level goal of the task,
rather than merely mimicking optimal behaviour. Similarly to

[4], we modify the gridworld environment by blocking the
optimal path with a wall (Fig. 4a). We first trained INFORM
in the original gridworld and recovered a reward function
using equation. Using this recovered reward function, we
trained new agents in the modified environment, without any
human feedback. These agents were trained using tabular Qlearning across 300 episodes for ease of implementation. To
compare the performances, we train similar agents using the
environmental reward (+1 for reaching the goal, 0 otherwise).
Figure 6 illustrates the learning performance in this modified
environment. The results show that the agents learning with
INFORM reward effectively converge to the optimal policy,
paralleling expert performance, and more rapidly than agents
learning with the environment reward. Further analysis of the
reward function revealed the one recovered from INFORM is
denser than the environmental reward, providing agents with
more information about the environment, which allows a faster
convergence of the policy.
In contrast, when evaluating TAMER-trained policies in this
modified setting (without further training), it was observed
that they uniformly failed to achieve the goal. These policies,
developed from direct human feedback, did not incorporate
adjustments for the new wall, requiring additional human
guidance to adapt to these environmental changes.


VII. CONCLUSION


In this study, we presented a sleep-inspired framework
that consolidates learning from human feedback. Initially,
our model learns a myopic policy through human feedback,



![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-5.png)

![](C:/Users/cerub/OneDrive/Dokumente/LLM/Research/converted_md/Learning while Sleeping Integrating Sleep-Inspired Consolidation with Human Feedback Learning_extracted/images/Learning-while-Sleeping-Integrating-Sleep-Inspired-Consolidation-with-Human-Feedback-Learning.pdf-5-6.png)
200


175


150


125


100


75


50


25



Gridworld with wall in optimal path (n=5)

|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|Col9|
|---|---|---|---|---|---|---|---|---|
||||||||||
|||||||~~Env rew~~<br>INFORM<br>|~~ ard~~<br> reward||
|||||||<br>TAMER<br>Expert|||
||||||||||
||||||||||
||||||||||
||||||||||
||||||||||



0 10000 20000 30000 40000 50000
Env steps



Fig. 6: Learning curve of agents in the gridworld with a wall
blocking the optimal path. Agents learning with INFORM
reward successfully and rapidly learn an optimal policy


then employs offline inverse reinforcement learning (RL) on
past experiences to simulate sleep consolidation and enhance
learning.
Our comparative evaluation of benchmark RL environments
demonstrated that INFORM effectively acquires high-level
optimal policies in both discrete and continuous tasks, showcasing its robustness against dynamic changes. Moreover,
the reward function retrieved by INFORM aligns with the
high-level objectives of tasks, enabling scalable autonomous
learning.
This research lays the groundwork for future exploration
in consolidation learning from human feedback. Subsequent
studies could validate the framework further by testing live
human-robot interaction and examining the influence of human
irrationality in providing feedback on INFORM’s effectiveness. Furthermore, future works should investigate the impact
of the quality and amount of data available during learning
with humans for the consolidation to be effective.


ACKNOWLEDGEMENT


We would like to thank Sarah Hamburg for her invaluable
neuroscience insights and for reviewing an earlier version of
this manuscript.


REFERENCES


[1] B. Wisniewski, K. Zierer, and J. Hattie, “The power of feedback
revisited: A meta-analysis of educational feedback research,” _Frontiers_
_in_ _Psychology_, vol. 10, p. 3087, 2020.

[2] A. L. Thomaz and C. Breazeal, “Teachable robots: Understanding human
teaching behavior to build more effective robot learners,” _Artificial_
_Intelligence_, vol. 172, no. 6-7, pp. 716–737, 2008.

[3] M. K. Ho, F. Cushman, M. L. Littman, and J. L. Austerweil, “People
teach with rewards and punishments as communication, not reinforcements.” _Journal_ _of_ _Experimental_ _Psychology:_ _General_, vol. 148, no. 3,
p. 520, 2019.

[4] W. B. Knox and P. Stone, “Framing reinforcement learning from
human reward: Reward positivity, temporal discounting, episodicity, and
performance,” _Artificial_ _Intelligence_, vol. 225, pp. 24–50, 2015.

[5] R. Stickgold, “Sleep-dependent memory consolidation,” _Nature_, vol.
437, no. 7063, pp. 1272–1278, 2005.

[6] R. Huber, M. Felice Ghilardi, M. Massimini, and G. Tononi, “Local
sleep and learning,” _Nature_, vol. 430, no. 6995, pp. 78–81, 2004.

[7] D. S. Ramanathan, T. Gulati, and K. Ganguly, “Sleep-dependent reactivation of ensembles in motor cortex promotes skill consolidation,” _PLoS_
_biology_, vol. 13, no. 9, p. e1002263, 2015.




[8] M. K. Ho and T. L. Griffiths, “Cognitive science as a source of forward
and inverse models of human decisions for robotics and control,” _Annual_
_Review_ _of_ _Control,_ _Robotics,_ _and_ _Autonomous_ _Systems_, vol. 5, pp. 33–
53, 2022.

[9] D. Garg, S. Chakraborty, C. Cundy, J. Song, and S. Ermon, “Iq-learn:
Inverse soft-q learning for imitation,” _Advances_ _in_ _Neural_ _Information_
_Processing_ _Systems_, vol. 34, pp. 4028–4039, 2021.

[10] R. S. Sutton and A. G. Barto, _Reinforcement_ _learning:_ _An_ _introduction_ .
MIT press, 2018.

[11] A. Y. Ng, S. Russell _et_ _al._, “Algorithms for inverse reinforcement
learning.” in _Icml_, vol. 1, 2000, p. 2.

[12] W. B. Knox and P. Stone, “Interactively shaping agents via human
reinforcement: The tamer framework,” in _Proceedings_ _of_ _the_ _fifth_ _in-_
_ternational_ _conference_ _on_ _Knowledge_ _capture_, 2009, pp. 9–16.

[13] A. Najar, O. Sigaud, and M. Chetouani, “Training a robot with evaluative feedback and unlabeled guidance signals,” in _2016_ _25th_ _IEEE_
_international symposium on robot and human interactive communication_
_(RO-MAN)_ . IEEE, 2016, pp. 261–266.

[14] G. Warnell, N. Waytowich, V. Lawhern, and P. Stone, “Deep tamer:
Interactive agent shaping in high-dimensional state spaces,” in _Proceed-_
_ings_ _of_ _the_ _AAAI_ _conference_ _on_ _artificial_ _intelligence_, vol. 32, no. 1,
2018.

[15] J. MacGlashan, M. K. Ho, R. Loftin, B. Peng, G. Wang, D. L. Roberts,
M. E. Taylor, and M. L. Littman, “Interactive learning from policydependent human feedback,” in _International_ _Conference_ _on_ _Machine_
_Learning_ . PMLR, 2017, pp. 2285–2294.

[16] D. Arumugam, J. K. Lee, S. Saskin, and M. L. Littman, “Deep
reinforcement learning from policy-dependent human feedback,” _arXiv_
_preprint_ _arXiv:1902.04257_, 2019.

[17] E. Massi, J. Barth´elemy, J. Mailly, R. Dromnelle, J. Canitrot, E. Poniatowski, B. Girard, and M. Khamassi, “Model-based and model-free
replay mechanisms for reinforcement learning in neurorobotics,” _Fron-_
_tiers_ _in_ _Neurorobotics_, vol. 16, p. 864380, 2022.

[18] D. Tirumala, T. Lampe, J. E. Chen, T. Haarnoja, S. Huang, G. Lever,
B. Moran, T. Hertweck, L. Hasenclever, M. Riedmiller _et_ _al._, “Replay
across experiments: A natural extension of off-policy rl,” _arXiv_ _preprint_
_arXiv:2311.15951_, 2023.

[19] S. Brodt, M. Inostroza, N. Niethard, and J. Born, “Sleep—a brain-state
serving systems memory consolidation,” _Neuron_, vol. 111, no. 7, pp.
1050–1075, 2023.

[20] M. Towers, J. K. Terry, A. Kwiatkowski, J. U. Balis, G. d.
Cola, T. Deleu, M. Goul˜ao, A. Kallinteris, A. KG, M. Krimmel,
R. Perez-Vicente, A. Pierr´e, S. Schulhoff, J. J. Tai, A. T. J. Shen,
and O. G. Younis, “Gymnasium,” Mar. 2023. [Online]. Available:
https://zenodo.org/record/8127025

[21] R. Zhang, D. Bansal, Y. Hao, A. Hiranaka, J. Gao, C. Wang, R. Mart´ınMart´ın, L. Fei-Fei, and J. Wu, “A dual representation framework for
robot learning with human guidance,” in _Conference on Robot Learning_ .
PMLR, 2023, pp. 738–750.

[22] M. K. Ho, J. MacGlashan, M. L. Littman, and F. Cushman, “Social is
special: A normative framework for teaching with and learning from
evaluative feedback,” _Cognition_, vol. 167, pp. 91–106, 2017.

[23] V. Mnih, K. Kavukcuoglu, D. Silver, A. A. Rusu, J. Veness, M. G.
Bellemare, A. Graves, M. Riedmiller, A. K. Fidjeland, G. Ostrovski
_et_ _al._, “Human-level control through deep reinforcement learning,”
_nature_, vol. 518, no. 7540, pp. 529–533, 2015.

[24] T. Haarnoja, A. Zhou, P. Abbeel, and S. Levine, “Soft actor-critic: Offpolicy maximum entropy deep reinforcement learning with a stochastic
actor,” in _International_ _conference_ _on_ _machine_ _learning_ . PMLR, 2018,
pp. 1861–1870.

[25] S. Huang, R. F. J. Dossa, C. Ye, J. Braga, D. Chakraborty, K. Mehta,
and J. G. Ara´ujo, “Cleanrl: High-quality single-file implementations of
deep reinforcement learning algorithms,” _Journal_ _of_ _Machine_ _Learning_
_Research_, vol. 23, no. 274, pp. 1–18, 2022. [Online]. Available:
http://jmlr.org/papers/v23/21-1342.html

[26] B. Eysenbach and S. Levine, “Maximum entropy rl (provably) solves
some robust rl problems,” _arXiv_ _preprint_ _arXiv:2103.06257_, 2021.


