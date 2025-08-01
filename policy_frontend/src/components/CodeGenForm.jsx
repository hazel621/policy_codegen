import React, { useState } from "react";

const examples = {
  dpcl: `power request_data{
    holder: patient
    action: #request_data
    consequence: +duty send_data{
			holder: hospital 
			counterparty: patient 
			action: #send_data 
			consequence: "data sent"
			violation: {condition: {"timeout":"72h"}}
            }
    }
    + duty send_data -> + power send_data{
        action: #send_data
        consequence: "data sent"
        holder: hospital               
    }
    + duty send_data.violation => +power report_fine{
    holder: patient 
    action:#report_fine
    consequence: "fine issued"
    }`,
  roles: `[
  {
    "uid": "r1",
    "role_name": "doctor",
    "description": "Handles treatment",
    "scope": "default",
    "powers": [
      {
        "power_id": "p1",
        "initial_state": "active",
        "scope": "hospital"
      }
    ],
    "duties": [
      {
        "duty_id": "d1",
        "initial_state": "assigned",
        "counterparty_role_id": "patient",
        "scope": "oncology"
      }
    ]
  }
]`,
  actions: `[
  {
    "uid": "request_access",
    "action_type": "#request_access",
    "consequence": {
        "operation": [
            {
                "type": "activate_duty",
                "parameter": {
                    "duty_id": "send_data",
                    "counterparty_role_id": "counterparty_role_id",
                    "counterparty_agent_id": "counterparty_agent_id"
                }
            }
        ]
    }
  }
]`,
  duties: `[
  {
    "uid": "d1",
    "action_type": "return_data",
    "action_id": "a1",
    "counterparty_id": "agent123",
    "counterparty_role_id": "patient",
    "violation_id": "v1"
  }
]`,
  powers: `[
  {
    "uid": "p1",
    "action_type": "revoke_access",
    "action_id": "a1"
  }
]`,
  violations: `[
    {
        "uid": "v_send_data",
        "condition": {
            "type": "timeout",
            "time": "72h"
        },
        "consequence": {
            "operation": [
                {
                    "type": "add_power",
                    "target_agent": "requester",
                    "power_id": "report_fine"
                }
            ]
        }
    }
]`,
  "action-handlers": `{
    "action_id": "change_data",
    "action_type": "change_data",
    "action_scope": "hospital_1",
    "operation": [
      {
        "type": "notify",
        "parameter": {
          "message": "data of {target_agent_id} changed by doctor",
          "target_agent_id": "from_request"
        }
      }
    ]
}`,
};

export default function CodegenSubmitPanel() {
  const [endpoint, setEndpoint] = useState("dpcl");
  const [inputJson, setInputJson] = useState(examples["dpcl"]);
  const [result, setResult] = useState("");

  const handleDpclSubmit = async (dpclText) => {
    try {
      const res = await fetch("http://localhost:8080/codegen/dpcl", {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: dpclText,
      });
      const text = await res.text();
      console.log("Raw response from /dpcl:", text); // debug

      const parsed = JSON.parse(text); 
      // const parsed = await res.json();
      // let steps = [];
      setResult(JSON.stringify(parsed, null, 2));
    } catch (err) {
      setResult("❌ DPCL processing failed: " + err.message);
    }
  };

  const handleEndpointChange = (e) => {
    const selected = e.target.value;
    setEndpoint(selected);
    setInputJson(examples[selected]);
    setResult("");
  };

  const resetToExample = () => {
    setInputJson(examples[endpoint]);
    setResult("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
  
    if (endpoint === "dpcl") {
      return await handleDpclSubmit(inputJson);
    }
  
    let jsonData;
    try {
      jsonData = JSON.parse(inputJson);
    } catch (err) {
      setResult("❌ Invalid JSON: " + err.message);
      return;
    }
  
    try {
      const res = await fetch(`http://localhost:8080/codegen/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(jsonData),
      });
  
      const data = await res.json();
      // console.log("Raw response from /codegen:", data); 
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setResult("❌ Request failed: " + err.message);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.panel}>
        <h2 style={styles.title}>🪄 Policy Code Generation</h2>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>Select Policy Component:</label>
          <select
            value={endpoint}
            onChange={handleEndpointChange}
            style={styles.input}
          >
            {Object.keys(examples).map((ep) => (
              <option key={ep} value={ep}>
                {ep}
              </option>
            ))}
          </select>

          <label style={styles.label}>
            Describe Policy Specification in JSON:
          </label>
          <textarea
            rows={20}
            value={inputJson}
            onChange={(e) => setInputJson(e.target.value)}
            style={{
              ...styles.input,
              fontFamily: "monospace",
              whiteSpace: "pre-wrap",
            }}
          />

          <div style={{ display: "flex", gap: "12px" }}>
            <button type="submit" style={styles.button}>
              Generate Code
              {/* Send POST to /{endpoint} */}
            </button>
            <button
              type="button"
              onClick={resetToExample}
              style={styles.resetButton}
            >
              Reset to Example
            </button>
          </div>
        </form>

        {result && (
          <div style={styles.resultBox}>
            {(() => {
              try {
                const parsed = JSON.parse(result);
                const steps = parsed.message
                  ?.split(";")
                  .map((s) => s.trim())
                  .filter((s) => s.length > 0);

                return (
                  <div>
                    {/* <strong>Status:</strong>{" "} */}
                    <span
                      style={{
                        color: parsed.status === "finished" ? "green" : "red",
                      }}
                    >
                      {parsed.status === "finished"
                        ? "✅ Success"
                        : `❌ ${parsed.status}`}
                    </span>
                    <br />
                    <strong>Details:</strong>
                    <ul style={{ paddingLeft: "1.5rem", marginTop: "0.5rem" }}>
                      {steps.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                );
              } catch (err) {
                return <pre style={styles.resultText}>{result}</pre>;
              }
            })()}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: "100vh",
    minWidth: "100vw",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    background: "#f5f7fa",
    padding: "20px",
  },
  panel: {
    width: "720px",
    // height: "600px",
    background: "#fff",
    padding: "30px",
    borderRadius: "12px",
    boxShadow: "0 0 12px rgba(0,0,0,0.1)",
  },
  title: {
    fontSize: "24px",
    marginBottom: "20px",
    color: "#333",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  label: {
    fontWeight: "bold",
  },
  input: {
    padding: "10px",
    borderRadius: "6px",
    border: "1px solid #ccc",
    fontSize: "14px",
  },
  button: {
    backgroundColor: "#007bff",
    color: "#fff",
    border: "none",
    padding: "12px",
    borderRadius: "6px",
    cursor: "pointer",
    flex: 1,
  },
  resetButton: {
    backgroundColor: "#e0e0e0",
    color: "#333",
    border: "none",
    padding: "12px",
    borderRadius: "6px",
    cursor: "pointer",
    flex: 1,
  },
  resultBox: {
    marginTop: "20px",
    background: "#f1f1f1",
    padding: "12px",
    borderRadius: "6px",
    maxHeight: "300px",
    overflowY: "auto",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  resultText: {
    fontSize: "14px",
    lineHeight: "1.5",
  },
};
