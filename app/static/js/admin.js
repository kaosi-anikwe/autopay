var names = [];

const handleInput = () => {
  // Get the input value
  const input = document.getElementById("name").value.toLowerCase();

  // Filter the data based on the input
  const checkNames = names.map((name) => name[0]);
  const filteredData = input
    ? checkNames.filter(function (item) {
        return item.toLowerCase().includes(input);
      })
    : [];

  // Display the filtered data as autocomplete items
  displayAutocompleteItems(filteredData);
};

const displayAutocompleteItems = (items) => {
  const autocompleteItemsContainer =
    document.getElementById("autocompleteItems");

  autocompleteItemsContainer.hidden = false;

  // Clear previous items
  autocompleteItemsContainer.innerHTML = "";

  // Create and append a box for each item
  items.forEach(function (item) {
    const box = document.createElement("div");
    box.className = "autocomplete-item";
    box.textContent = item;
    box.onclick = function () {
      // Fill the input field when a box is clicked
      document.getElementById("name").value = item;
      // Get Reg No
      const phoneNo = names
        .filter((name) => name[0] === item)
        .map((name) => name[1])[0];
      document.getElementById("phone_no").value = phoneNo;
      // Clear the autocomplete items
      autocompleteItemsContainer.innerHTML = "";
      autocompleteItemsContainer.hidden = true;
    };
    autocompleteItemsContainer.appendChild(box);
  });
};

const getNames = async () => {
  const part = document.getElementById("part").value;
  const fee_type = document.getElementById("fee_type").value;
  const mode = document.getElementById("current-mode").innerText;
  const nameDiv = document.getElementById("name-div");
  document.getElementById("name").value = "";
  document.getElementById("phone_no").value = "";
  if (part === "Donations" || mode.toLowerCase().includes("name")) {
    document.getElementById("name").required = false;
    document.getElementById("phone_no").required = false;
    document.getElementById("name").removeEventListener("input", handleInput);
  } else {
    document.getElementById("name").required = true;
    document.getElementById("phone_no").required = true;
    document.getElementById("name").addEventListener("input", handleInput);
  }
  try {
    nameDiv.classList.toggle("running");
    let response = await fetch(`/names?part=${part}&fee_type=${fee_type}`);
    if (response.ok) {
      let data = await response.json();
      if (data.names) {
        names = data.names;
        document.getElementById("name").disabled = false;
      }
    } else {
      alert("Error getting parts. Try refreshing the page");
      let error = await response.json();
      console.log(error);
    }
  } catch (error) {
    alert("An error occured. Please try again later or contact the admins.");
    console.log(error);
  } finally {
    nameDiv.classList.toggle("running");
  }
};

document.getElementById("alt-mode").addEventListener("click", (e) => {
  e.preventDefault();
  const alt = e.target;
  const current = document.getElementById("current-mode");
  const changeName = alt.innerText;
  alt.innerText = current.innerText;
  current.innerText = changeName;
  document.getElementById("form-message-success").hidden = true;
  document.getElementById("autocompleteItems").hidden = true;
});

document.getElementById("alt-mode").addEventListener("click", () => {
  document.getElementById("name").value = "";
  document.getElementById("phone_no").value = "";
  const current = document.getElementById("current-mode");
  if (current.innerText.toLowerCase().includes("payment")) {
    document.getElementById("amount-div").hidden = false;
    document.getElementById("amount").required = true;
    document.getElementById("name").required = true;
    document.getElementById("name").addEventListener("input", handleInput);
  } else {
    document.getElementById("amount-div").hidden = true;
    document.getElementById("amount").required = false;
    document.getElementById("name").required = false;
    document.getElementById("name").removeEventListener("input", handleInput);
  }
});

document.getElementById("adminForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = document.getElementById("current-mode").innerText;
  const formDiv = document.getElementById("adminForm");
  const mssg = document.getElementById("form-message-success");
  mssg.hidden = true;
  formDiv.classList.toggle("running");
  if (mode.toLowerCase().includes("payment")) {
    // check for donation
    const input = document.getElementById("name").value.toLowerCase();
    const checkNames = names.map((name) => name[0]);
    const filteredData = input
      ? checkNames.filter(function (item) {
          return item.toLowerCase().includes(input);
        })
      : [];
    if (!filteredData[0]) {
      document.getElementById("part").value = "Donations";
    }
  }
  try {
    if (mode.toLowerCase().includes("name")) {
      // handle name submission
      const fee_type = document.getElementById("fee_type").value;
      const part = document.getElementById("part").value;
      const name = document.getElementById("name").value;
      const phone_no = document.getElementById("phone_no").value;
      const formData = new FormData();
      formData.append("fee_type", fee_type);
      formData.append("part", part);
      formData.append("name", name);
      formData.append("phone_no", phone_no);
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
        document.getElementById("name").value = "";
        document.getElementById("phone_no").value = "";
      } else {
        alert(
          "Failed to add name. Check spreadsheet to confirm if record already exists."
        );
        let error = await response.json();
        console.log(error);
      }
    }
    if (mode.toLowerCase().includes("payment")) {
      // handle payment submission
      const fee_type = document.getElementById("fee_type").value;
      const part = document.getElementById("part").value;
      const name = document.getElementById("name").value;
      const amount = document.getElementById("amount").value;
      const phone_no = document.getElementById("phone_no").value;
      const donation = document.getElementById("part").value === "Donations";
      const payload = { fee_type, part, name, amount, phone_no, donation };
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
    if (mode.toLowerCase().includes("name")) {
      await getNames();
    }
  }
});

document.getElementById("part").addEventListener("change", getNames);
document.getElementById("fee_type").addEventListener("change", getNames);
document.addEventListener("DOMContentLoaded", getNames);
document.getElementById("name").removeEventListener("input", handleInput);
