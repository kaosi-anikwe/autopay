document.getElementById("alt-mode").addEventListener("click", (e) => {
  e.preventDefault();
  const alt = e.target;
  const current = document.getElementById("current-mode");
  const changeName = alt.innerText;
  alt.innerText = current.innerText;
  current.innerText = changeName;
  document.getElementById("form-message-success").hidden = true;
});

document.getElementById("alt-mode").addEventListener("click", () => {
  const current = document.getElementById("current-mode");
  if (current.innerText.includes("payment")) {
    document.getElementById("amount-div").hidden = false;
    document.getElementById("amount-div").required = true;
    document.getElementById("name").required = true;
    document.getElementById("file-div").hidden = true;
  } else {
    document.getElementById("amount-div").hidden = true;
    document.getElementById("amount-div").required = false;
    document.getElementById("name").required = false;
    document.getElementById("file-div").hidden = false;
  }
});

document.getElementById("adminForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = document.getElementById("current-mode").innerText;
  const formDiv = document.getElementById("adminForm");
  const mssg = document.getElementById("form-message-success");
  mssg.hidden = true;
  formDiv.classList.toggle("running");
  try {
    if (mode.includes("name")) {
      // handle payment submission
      const fee_type = document.getElementById("fee_type").value;
      const part = document.getElementById("part").value;
      const name = document.getElementById("name").value;
      const nameFile = document.getElementById("name-file");
      const formData = new FormData();
      formData.append("name-file", nameFile);
      formData.append("fee_type", fee_type);
      formData.append("part", part);
      formData.append("name", name);
      let response = await fetch("/add-name", {
        method: "POST",
        headers: {
          "X-CSRFToken": document.getElementById("csrf_token").value,
        },
        body: formData,
      });
      if (response.ok) {
        mssg.innerText = "Added successfully!";
        mssg.hidden = false;
      } else {
        alert("Failed to add name. Please refresh the page and try again.");
        let error = await response.json();
        console.log(error);
      }
    }
    if (mode.includes("payment")) {
      // handle name submission
      const fee_type = document.getElementById("fee_type").value;
      const part = document.getElementById("part").value;
      const name = document.getElementById("name").value;
      const amount = document.getElementById("amount").value;
      const payload = { fee_type, part, name, amount };
      let response = await fetch("/add-payment", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.getElementById("csrf_token").value,
        },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        mssg.innerText = "Added successfully!";
        mssg.hidden = false;
      } else {
        alert("Failed to add payment. Please refresh the page and try again.");
        let error = await response.json();
        console.log(error);
      }
    }
  } catch (error) {
    alert("Something went wrong. Please refresh the page and try again.");
    console.log(error);
  } finally {
    formDiv.classList.toggle("running");
  }
});
