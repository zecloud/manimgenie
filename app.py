from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from manimgenie.sessionpythonrepltool import SessionsPythonREPLTool,CodeBlock,extract_markdown_code_blocks
import os
import chainlit as cl
import re


apikey=os.getenv("AZUREOPENAIAPIKEY")
azure_resource_name =os.environ.get('AZRESOURCE_NAME')
azure_deployment_name =os.environ.get('AZDEPLOYMENT_NAME')
BASE_URL = "https://"+azure_resource_name+".openai.azure.com"
model = AzureChatOpenAI(streaming=False,
                                azure_endpoint=BASE_URL,
    openai_api_version="2024-12-01-preview",
    deployment_name=azure_deployment_name,
    openai_api_key=apikey,temperature=1)

sessionpoolurl=os.environ.get('AZSESSIONPOOLURL')

@cl.on_chat_start
async def on_chat_start():#

    prompt= PromptTemplate(input_variables=["question"], 
                           template="""You're a Computer Scientist specializing in AI. You're asked to provide detailed a
                           nd eloquent answers to AI questions.\n
                           Create python code to generate a video with manim that explains the following question: \n
                           {question}
                           Remember ShowCreation() is deprecated, replace it with Create() \n
                           Passing Mobject methods to Scene.play is no longer supported. Use Mobject.animate instead \n
                            \n\n
                            Respond only with the code in a markdown block""")
    

   
    chain = (prompt  | model | StrOutputParser())
    cl.user_session.set("chain", chain)


@cl.on_message
async def on_message(message: cl.Message):
    chain = cl.user_session.get("chain") 
    res =await chain.ainvoke({"question":message.content}, config={"callbacks": [cl.LangchainCallbackHandler()]})
   

    await cl.Message(content=res).send()
    codeblock=extract_markdown_code_blocks(res)
    codeblock=codeblock[0]
    await exec_step(codeblock)

@cl.step(name="Python_Execution")
async def exec_step(codeblock:CodeBlock):
     # Utiliser une expression régulière pour extraire le nom de la scène
    match = re.search(r'class\s+(\w+)', codeblock.code)
    if match:
        Scenename = match.group(1)
    else:
        return "No class name found in the code"
    pool_management_endpoint=sessionpoolurl
    repl = SessionsPythonREPLTool(pool_management_endpoint=pool_management_endpoint)

    resultmanim=await repl.ainvoke({"python_code":codeblock.code,"scene_name":Scenename})
    await cl.Message("Video Generated").send()
    promptfile="""respond only the file path when it is ready : \n
    {manimcode} \n
    """
    promptfile = PromptTemplate(input_variables=["manimcode"], template=promptfile)
    genpromptfile =await  (promptfile | model | StrOutputParser()).ainvoke({"manimcode":resultmanim})
    await cl.Message("Downloading remote path "+genpromptfile).send()
    vid=repl.download_file(remote_file_path=genpromptfile)
    with open(repl.session_id+".mp4", "wb") as f:
             f.write(vid.getvalue())
    elements = [
            cl.Video(name=repl.session_id+".mp4", path="./"+repl.session_id+".mp4", display="inline"),
        ]
    await cl.Message(
        content="Video is finished, here is the result:",
        elements=elements,
    ).send()
    return repl.session_id+".mp4"



