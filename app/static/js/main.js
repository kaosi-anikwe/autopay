var names = [];
var donate = false;

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
      // Clear the autocomplete items
      autocompleteItemsContainer.innerHTML = "";
      autocompleteItemsContainer.hidden = true;
    };
    autocompleteItemsContainer.appendChild(box);
  });
};

document.getElementById("paymentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.classList.toggle("running");
  try {
    if (!donate) {
      const input = document.getElementById("name").value.toLowerCase();
      const checkNames = names.map((name) => name[0]);
      const filteredData = input
        ? checkNames.filter(function (item) {
            return item.toLowerCase().includes(input);
          })
        : [];
      if (!filteredData[0]) {
        const mssg = document.getElementById("form-message-warning");
        mssg.innerText =
          "Your name is not registered. Please contact the admins. If you would like to donate, please check the box below.";
        mssg.hidden = false;
        return;
      }
    }
    const part = document.getElementById("part").value;
    const name = document.getElementById("name").value;
    const amount = document.getElementById("amount").value;
    const fee_type = document.getElementById("fee_type").value;
    const donation = document.getElementById("donate").checked;
    let payload = { part, donation };
    let response = await fetch("/tx_ref", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.getElementById("csrf_token").value,
      },
      body: JSON.stringify(payload),
    });
    if (response.ok) {
      let data = await response.json();
      const tx_ref = data.tx_ref;
      // Gather info for flutter wave and submit form
      document.getElementById("flw-tx_ref").value = tx_ref;
      document.getElementById("flw-amount").value = amount;
      document.getElementById("flw-fee_type").value = fee_type;
      document.getElementById("flw-part").value = part;
      document.getElementById("flw-donation").value = `${donation}`;
      document.getElementById("flw-name").value = name;
      // submit form
      if (
        confirm(
          "You will be redirected to Flutterwave to complete your payment."
        )
      ) {
        e.target.submit();
        submitBtn.disabled = true;
      }
    } else {
      alert("Something went wrong. Please refresh the page and try again.");
      let error = await response.json();
      console.log(error);
    }
  } catch (error) {
    alert("Something went wrong. Please refresh the page and try again");
    console.log(error);
  } finally {
    submitBtn.classList.toggle("running");
  }
});

const getNames = async () => {
  const nameDiv = document.getElementById("name-div");
  document.getElementById("name").value = "";
  try {
    nameDiv.classList.toggle("running");
    const part = document.getElementById("part").value;
    const fee_type = document.getElementById("fee_type").value;
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

document.getElementById("donate").addEventListener("change", (e) => {
  document.getElementById("form-message-warning").hidden = true;
  const nameInput = document.getElementById("name");
  if (e.target.checked) {
    donate = true;
    nameInput.removeEventListener("input", handleInput);
  } else {
    nameInput.addEventListener("input", handleInput);
  }
});

document.getElementById("part").addEventListener("change", getNames);
document.getElementById("fee_type").addEventListener("change", getNames);
document.addEventListener("DOMContentLoaded", getNames);
document.getElementById("name").addEventListener("input", handleInput);
