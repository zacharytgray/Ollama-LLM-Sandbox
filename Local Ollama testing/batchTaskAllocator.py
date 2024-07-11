import ollama
from colorama import Fore

class Agent:
	def __init__(self, name) -> None: # tasks are (task, skill) tuples
		self.name = name
		self.temperature = 0.4
		self.assignedTasks = []
		self.model = 'gemma2:latest'
		self.memoryBuffer = []
		self.systemInstructions = f"""
Your name is {self.name}. You will collaboratively allocate tasks with a partner based on two factors:
1. Skill Levels: use a scale from 1 (least skill) to 10 (highest skill). You will report your skill level for each task. Initially, you won't know your partner's skill levels.
2. Balanced Workload: Aim to distribute tasks evenly to avoid overloading one person.

Rules:
- Collaboration on tasks is forbidden. That is, only one of you should be assigned to each task. 
- Compare skill levels to assign tasks efficiently.
- Your assigned skill levels are permanently set, and you must not change them. When asked for your skill level for a task, you must provide the value given in the following section, "Tasks to Allocate".
- You must allocate all of the assigned tasks.
- Do not include any new line characters in your responses unless prompted to do so.

Remember: It's always a good idea to share your skill levels with your partner.

Tasks to Allocate:"""

	def addToMemoryBuffer(self, role, inputText): #role is either 'user', 'assistant', or 'system'
		self.memoryBuffer.append({'role':role, 'content': inputText})

	def queryModel(self):
		response = ollama.chat(model=self.model, messages=self.memoryBuffer, options = {'temperature': self.temperature,})
		return response['message']['content'].strip()
	
	def run(self, role, inputText):
		self.addToMemoryBuffer(role, inputText)
		response = self.queryModel()
		self.addToMemoryBuffer('assistant', response)
		if not response:
			print(f"{Fore.RED}Error: No response from model. Response: '{response}' {Fore.RESET}")
		return response
	
	def printMemoryBuffer(self, otherAgent):
		print(f"\n{Fore.YELLOW}{self.name}'s Memory Buffer:{Fore.RESET}")
		for dict in self.memoryBuffer:
			if dict.get('role') == 'system':
				print(Fore.RED + "System: " + dict.get('content') + Fore.RESET)
			elif dict.get('role') == 'user':
				print(Fore.BLUE + f"{otherAgent.name} (User): " + dict.get('content') + Fore.RESET)
			elif dict.get('role') == 'assistant':
				print(Fore.GREEN + f"{self.name} (Assistant): " + dict.get('content') + Fore.RESET)
			else:
				print(f"{Fore.RED}Error: Invalid role in memory buffer: {dict.get('role')}")
				print(f"Content: {dict.get('content')}{Fore.RESET}")

	def addTask(self, task):
		self.assignedTasks.append(task)

	def numTasks(self):
		return len(self.tasks)
	
class Domain:
	def __init__(self, agent1, agent2, tasks) -> None:
		self.agent1 = agent1
		self.agent2 = agent2
		self.tasks = tasks
		for i, task in enumerate(self.tasks, start=1):
			taskDescription, skill1, skill2 = task
			agent1.systemInstructions +=  f"\n- {taskDescription}: {agent1.name}'s skill level for this task is {skill1} out of 10."
			agent2.systemInstructions +=  f"\n- {taskDescription}: {agent2.name}'s skill level for this task is {skill2} out of 10."
		
		agent1.systemInstructions += "\n\nLet's begin! Be concise."
		agent2.systemInstructions += "\n\nLet's begin! Be concise."

	def getConsensus(self): #returns True if both agents agree on who should be assigned the task
		consensusString = """Now, based on the conversation you just had with your partner, you must determine who will get assigned each task. 
Rules:
- Your results must be based on the conversation you just had.
- You must respond in the following manner:\n"""
		for task in self.tasks:
			taskDescription = task[0]
			consensusString += f"\n{taskDescription}:AGENT_NAME_FOR_THIS_TASK"
		
		consensusString += f"""\n
Where 'AGENT_NAME_FOR_THIS_TASK' is the name of the agent you think should be assigned that task.
- Do not respond with anything other than what's shown above.
"""
		rawConsensus1 = self.agent1.run("system", consensusString).strip().lower()
		rawConsensus2 = self.agent2.run("system", consensusString).strip().lower()
		consensus1 = rawConsensus1.split("\n") # gives ['task name:agent name', ...]
		consensus2 = rawConsensus2.split("\n") # gives ['task name:agent name', ...]
		agreedIndex = [] #list of indices where the agents agree on who should be assigned the task. True is agree, False is disagree
		agent1Choices = []
		agent2Choices = []

		# Consensus Logic:
		for i, task in enumerate(self.tasks):
			taskDescription = task[0]
			agent1Choice = consensus1[i].split(":")[1].lower().strip()
			agent2Choice = consensus2[i].split(":")[1].lower().strip()

			agent1Choices.append(agent1Choice)
			agent2Choices.append(agent2Choice)

			if agent1Choice == agent2Choice:
				agreedIndex.append(True)
			else:
				agreedIndex.append(False)
		if False in agreedIndex:
			print(f"\n{Fore.RED}Consensus not reached: {agreedIndex}{Fore.RESET}")
			self.agent1.run("system", "Consensus not reached. Please continue discussing the task allocation until you are asked to vote again.")
			self.agent2.run("system", "Consensus not reached. Please continue discussing the task allocation until you are asked to vote again.")
			return False
		else:
			for i, task in enumerate(self.tasks): # assign tasks based on consensus
				if agent1Choices[i] == self.agent1.name.lower():
					self.agent1.addTask(task)
				else:
					self.agent2.addTask(task)
			return True

	def printTasks(self):
		print(f"\n{Fore.YELLOW}{self.agent1.name}'s tasks: {self.agent1.assignedTasks}")
		print(f"{self.agent2.name}'s tasks: {self.agent2.assignedTasks}{Fore.RESET}")
	
	def interruptConversation(self): #interrupt the conversation to allow the user to talk to agents directly
		#Type 1 to talk to agent 1
		#Type 2 to talk to agent 2
		#Type mb to see memory buffer
		#Type c to continue conversation

		userInput = ""
		while userInput.lower() != "c":
			userInput = input(f"\n{Fore.GREEN}What would you like to do? (1, 2, mb, c): {Fore.RESET}")
			if userInput != "c":
				if userInput == "1": #user wants to talk to agent 1
					userInput = input(f"Chat to Agent 1 ({self.agent1.name}): ")
					response = self.agent1.run("user", userInput)
					print(f"{self.agent1.name}: {response}")
				elif userInput == "2": #user wants to talk to agent 2
					userInput = input(f"Chat to Agent 2 ({self.agent2.name}): ")
					response = self.agent2.run("user", userInput)
					print(f"{self.agent2.name}: {response}")
				elif userInput == "mb": #user wants to see memory buffer
					self.agent1.printMemoryBuffer(self.agent2)
					self.agent2.printMemoryBuffer(self.agent1)
				else: 
					print("Pass...")

	def assignTasks(self):
		numIterations = 6
		self.agent1.addToMemoryBuffer('system', self.agent1.systemInstructions)
		self.agent2.addToMemoryBuffer('system', self.agent2.systemInstructions)
		
		currentInput = f"Hello! I'm {self.agent2.name}. Let's begin the task allocation."
		self.agent2.addToMemoryBuffer('assistant', currentInput)
	
		currentAgent = self.agent1
		consensusReached = False

		while not consensusReached:

			for i in range(numIterations):
				response = currentAgent.run("user", currentInput)
				if currentAgent == self.agent1:
					print(f"{Fore.CYAN}\n{currentAgent.name}: \n	{response.strip()}{Fore.RESET}")
				elif currentAgent == self.agent2:
					print(f"{Fore.GREEN}\n{currentAgent.name}: \n	{response.strip()}{Fore.RESET}")

				currentAgent = self.agent2 if currentAgent == self.agent1 else self.agent1
				currentInput = response

				if i == (numIterations-1): # Manually add final dialogue to agent 2
					self.agent2.addToMemoryBuffer('user', currentInput)

				# uncomment to allow user to talk to agents directly inbetween messages or see memory buffers live
				# self.interruptConversation() 

			consensusReached = self.getConsensus()

		self.printTasks()

def main():
	agent1 = Agent("Finn")
	agent2 = Agent("Jake")
	tasks = [("Word search", 6, 4), ("Math game", 8, 2), ("Geography game", 9, 3), ("Trivia", 7, 5), ("Puzzle", 6, 3)]
	domain = Domain(agent1, agent2, tasks)
	domain.assignTasks()

	# agent1.printMemoryBuffer(otherAgent = agent2)
	# agent2.printMemoryBuffer(otherAgent = agent1)

if __name__ == main():
	
	main()