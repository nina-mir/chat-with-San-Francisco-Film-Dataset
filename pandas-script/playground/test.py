from code_gen_system_instructions import make_code_gen_instructions 

preprocessing_str = 'first'
nlp_plan_str = 'second'

updated_content = make_code_gen_instructions(preprocessing_str, nlp_plan_str)


print(updated_content)


# from pathlib import Path

# code_gen_system_instructions = 'code_gen_system_instructions.md'

# system_instructions = Path.cwd().joinpath("..").joinpath(code_gen_system_instructions).resolve()


# with open(system_instructions, 'r') as f:
#     content = f.read()

