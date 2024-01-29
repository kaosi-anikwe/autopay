const updateInfo = () => {
  const fee_type = document.getElementById("fee_type").value;
  const title = pageInfo[fee_type].title;
  const info = pageInfo[fee_type].info;
  document.getElementById("page-title").innerHTML = title;
  document.getElementById("page-info").innerHTML = info;
};

document.getElementById("fee_type").addEventListener("change", updateInfo);
document.addEventListener("DOMContentLoaded", updateInfo);
