import React, { useState, useEffect } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";

const Tp = () => {
  const [typedInput, setTypedInput] = useState("");
  const [loader, setLoader] = useState(false);
  const [editedQuery, setEditedQuery] = useState("");
  const [queryResult, setQueryResult] = useState([]);
  const [columnNames, setColumnNames] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [queryStatusLabel, setQueryStatusLabel] = useState("");

  const { transcript, listening, resetTranscript } = useSpeechRecognition();

  useEffect(() => {
    if (loader) {
      setQueryStatusLabel("Query is being generated...");
    } else if (editedQuery !== "") {
      setQueryStatusLabel("Query is generated.");
    } else if (queryResult.length > 0) {
      setQueryStatusLabel("Results :");
    } else {
      setQueryStatusLabel(""); // Empty string if none of the conditions are met
    }
  }, [loader, editedQuery, queryResult]);

  const sendQueryToBackend = async () => {
    try {
      setLoader(true);
      setErrorMessage(""); // Clear any previous error messages
      const response = await fetch("http://localhost:5000/generate-sql-query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: transcript || typedInput }),
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const data = await response.json();
      setEditedQuery(data.sql_query);
    } catch (error) {
      console.error("Error:", error);
      setErrorMessage("Error generating SQL query.");
    } finally {
      setLoader(false);
    }
  };

  const handleEditQuery = (event) => {
    setEditedQuery(event.target.value);
  };

  const handleConfirmQuery = async () => {
    try {
      // setLoader(true);
      setErrorMessage(""); // Clear any previous error messages
      const response = await fetch("http://localhost:5000/execute-sql-query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: editedQuery }),
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      const data = await response.json();
      setQueryResult(data.result);
      setColumnNames(data.column_names);
    } catch (error) {
      console.error("Error:", error);
      setErrorMessage("Error executing SQL query.");
    } finally {
      setEditedQuery("");
    }
  };

  const displayResult = () => {
    if (typeof queryResult === "string") {
      return <p>{queryResult}</p>;
    } else {
      return (
        <table>
          <thead>
            <tr>
              {columnNames.map((columnName, index) => (
                <th key={index}>{columnName}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {queryResult.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {Object.values(row).map((value, colIndex) => (
                  <td key={colIndex}>{value}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
  };

  return (
    <div className="container mb-5">
      <nav className="navbar border shadow p-3 mb-5 mt-5 rounded-3">
        <div className="container-fluid">
          <span className="navbar-brand mb-0 h1">Talking To Database!</span>
        </div>
      </nav>
      <div className="input-field">
        <div className="input-box">
          <input
            type="text"
            className="input"
            placeholder="Type or Record your prompt ..."
            aria-label="Input box with mic and send button"
            value={transcript || typedInput}
            onChange={(e) => setTypedInput(e.target.value)}
          />
          <div>
            <button className="btn" type="button" onClick={SpeechRecognition.startListening}>
              {listening ? <i className="bi bi-mic-fill"></i> : <i className="bi bi-mic-mute"></i>}
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                SpeechRecognition.stopListening();
                sendQueryToBackend();
              }}
            >
              <i className="bi bi-send"></i>
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                resetTranscript();
                setTypedInput("");
              }}
            >
              <i className="bi bi-x"></i>
            </button>
          </div>
        </div>
      </div>
      <div className="input-field">
        <div className="input-box">
          <input
            type="text"
            className="input"
            placeholder="Generated SQL Query will appear here ..."
            value={editedQuery}
            onChange={handleEditQuery}
          />
          <div className="spinner-container">
            {loader && (
              <div className="spinner-border text-light spinner-border-md" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            )}
            <button className="btn" type="button" onClick={handleConfirmQuery}>
              <i className="bi bi-send"></i>
            </button>
            <button className="btn" type="button" onClick={() => setEditedQuery("")}>
              <i className="bi bi-x"></i>
            </button>
          </div>
        </div>
      </div>
      <label>{queryStatusLabel}</label>
      {errorMessage && <p className="error-message">{errorMessage}</p>}
      {displayResult()}
    </div>
  );
};

export default Tp;
