"""
Generates p4_handshake.jmx (the JMeter test plan). Kept as code so the
plan is reviewable; the generated .jmx is committed too.

Thread groups (each runs only when its *_threads property is > 0):
  Login               POST /api/auth/login                       login_threads
  Job search          GET  /api/jobs?search=...                  search_threads
  Application submit  POST /api/applications (202 via Kafka)     apply_threads
  Event search        GET  /api/events?search=...                event_threads
  Assistant chat      POST /api/assistant/chat                   assistant_threads

    jmeter -n -t loadtest/p4_handshake.jmx -Jsearch_threads=200 -l out.jtl
"""

from xml.sax.saxutils import escape

HOST, PORT = "${__P(host,localhost)}", "${__P(port,9040)}"


def http(name, method, path, body=None, files=None, extract_token=False, params=None, assert_status=False):
    args = ""
    if body is not None:
        args = f'''<boolProp name="HTTPSampler.postBodyRaw">true</boolProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments">
              <elementProp name="" elementType="HTTPArgument">
                <boolProp name="HTTPArgument.always_encode">false</boolProp>
                <stringProp name="Argument.value">{escape(body)}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
              </elementProp>
            </collectionProp>
          </elementProp>'''
    elif params:
        items = "".join(f'''
              <elementProp name="{k}" elementType="HTTPArgument">
                <boolProp name="HTTPArgument.always_encode">true</boolProp>
                <stringProp name="Argument.name">{k}</stringProp>
                <stringProp name="Argument.value">{escape(v)}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
                <boolProp name="HTTPArgument.use_equals">true</boolProp>
              </elementProp>''' for k, v in params.items())
        args = f'''<elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments">{items}
            </collectionProp>
          </elementProp>'''
    file_xml = ""
    if files:
        file_xml = f'''<boolProp name="HTTPSampler.DO_MULTIPART_POST">true</boolProp>
          <elementProp name="HTTPsampler.Files" elementType="HTTPFileArgs">
            <collectionProp name="HTTPFileArgs.files">
              <elementProp name="{files}" elementType="HTTPFileArg">
                <stringProp name="File.path">{files}</stringProp>
                <stringProp name="File.paramname">resume</stringProp>
                <stringProp name="File.mimetype">application/pdf</stringProp>
              </elementProp>
            </collectionProp>
          </elementProp>'''
    extractor = ""
    if extract_token:
        extractor = '''
        <hashTree>
          <JSONPostProcessor guiclass="JSONPostProcessorGui" testclass="JSONPostProcessor" testname="Extract token" enabled="true">
            <stringProp name="JSONPostProcessor.referenceNames">token</stringProp>
            <stringProp name="JSONPostProcessor.jsonPathExprs">$.access_token</stringProp>
            <stringProp name="JSONPostProcessor.match_numbers">1</stringProp>
            <stringProp name="JSONPostProcessor.defaultValues">NO_TOKEN</stringProp>
          </JSONPostProcessor>
          <hashTree/>
        </hashTree>'''
    elif assert_status:
        # The assistant answers HTTP 200 even when the model timed out
        # (status model_error / timeout); count those as errors.
        extractor = '''
        <hashTree>
          <JSONPathAssertion guiclass="JSONPathAssertionGui" testclass="JSONPathAssertion" testname="status is final" enabled="true">
            <stringProp name="JSON_PATH">$.status</stringProp>
            <stringProp name="EXPECTED_VALUE">final|confirmation_required</stringProp>
            <boolProp name="JSONVALIDATION">true</boolProp>
            <boolProp name="EXPECT_NULL">false</boolProp>
            <boolProp name="INVERT">false</boolProp>
            <boolProp name="ISREGEX">true</boolProp>
          </JSONPathAssertion>
          <hashTree/>
        </hashTree>'''
    else:
        extractor = "\n        <hashTree/>"
    return f'''
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="{name}" enabled="true">
          {args}
          {file_xml}
          <stringProp name="HTTPSampler.domain">{HOST}</stringProp>
          <stringProp name="HTTPSampler.port">{PORT}</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">{path}</stringProp>
          <stringProp name="HTTPSampler.method">{method}</stringProp>
          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          <stringProp name="HTTPSampler.connect_timeout">10000</stringProp>
          <stringProp name="HTTPSampler.response_timeout">${{__P(response_timeout,60000)}}</stringProp>
        </HTTPSamplerProxy>{extractor}'''


def headers(auth=True, json_body=True):
    rows = []
    if json_body:
        rows.append(("Content-Type", "application/json"))
    if auth:
        rows.append(("Authorization", "Bearer ${token}"))
    items = "".join(f'''
            <elementProp name="" elementType="Header">
              <stringProp name="Header.name">{k}</stringProp>
              <stringProp name="Header.value">{v}</stringProp>
            </elementProp>''' for k, v in rows)
    return f'''
        <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="Headers" enabled="true">
          <collectionProp name="HeaderManager.headers">{items}
          </collectionProp>
        </HeaderManager>
        <hashTree/>'''


def csv(filename, names):
    return f'''
        <CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="{filename}" enabled="true">
          <stringProp name="filename">${{__P(data_dir,loadtest/data)}}/{filename}</stringProp>
          <stringProp name="variableNames">{names}</stringProp>
          <stringProp name="delimiter">,</stringProp>
          <boolProp name="ignoreFirstLine">true</boolProp>
          <boolProp name="recycle">true</boolProp>
          <boolProp name="stopThread">false</boolProp>
          <stringProp name="shareMode">shareMode.all</stringProp>
        </CSVDataSet>
        <hashTree/>'''


def group(name, prop, loops_prop, default_loops, body):
    return f'''
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="{name}" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <stringProp name="LoopController.loops">${{__P({loops_prop},{default_loops})}}</stringProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">${{__P({prop},0)}}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">${{__P(ramp,10)}}</stringProp>
        <boolProp name="ThreadGroup.delayedStart">false</boolProp>
      </ThreadGroup>
      <hashTree>{body}
      </hashTree>'''


login_body = '{"email":"${email}","password":"Pair4Demo!"}'

# Setup login inside a Once Only Controller so only the measured request repeats.
def once(inner):
    return f'''
        <OnceOnlyController guiclass="OnceOnlyControllerGui" testclass="OnceOnlyController" testname="Sign in once" enabled="true"/>
        <hashTree>{inner}
        </hashTree>'''


groups = [
    group("Login", "login_threads", "crud_loops", 5,
          csv("students.csv", "email") + headers(auth=False) + http("Login", "POST", "/api/auth/login", body=login_body)),
    group("Job search", "search_threads", "crud_loops", 5,
          csv("search_terms.csv", "term") + http("Job search", "GET", "/api/jobs", params={"search": "${term}"})),
    group("Application submission", "apply_threads", "apply_loops", 1,
          csv("apply_${__P(level,100)}.csv", "email,job_id")
          + once(headers(auth=False) + http("setup login (apply)", "POST", "/api/auth/login", body=login_body, extract_token=True))
          + headers(auth=True, json_body=False)
          + http("Application submission", "POST", "/api/applications", params={"job_id": "${job_id}"},
                 files="${__P(resume,loadtest/data/resume.pdf)}")),
    group("Event search", "event_threads", "crud_loops", 5,
          csv("search_terms.csv", "term") + http("Event search", "GET", "/api/events", params={"search": "${term}"})),
    group("Assistant chat", "assistant_threads", "assistant_loops", 1,
          csv("students.csv", "email")
          + once(headers(auth=False) + http("setup login (assistant)", "POST", "/api/auth/login", body=login_body, extract_token=True))
          + headers(auth=True)
          + http("Assistant chat", "POST", "/api/assistant/chat", body='{"message":"Find data science internships."}',
                 assert_status=True)),
]

plan = f'''<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Pair 4 Handshake load test" enabled="true">
      <stringProp name="TestPlan.comments">Generated by loadtest/build_plan.py. Run through loadtest/run_loadtest.sh.</stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>{"".join(groups)}
    </hashTree>
  </hashTree>
</jmeterTestPlan>
'''

open("loadtest/p4_handshake.jmx" if __import__("os").path.isdir("loadtest") else "p4_handshake.jmx", "w").write(plan)
print("wrote p4_handshake.jmx")
