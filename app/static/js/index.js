const updateInfo = () => {
  if (document.getElementById("fee_type")) {
    const fee_type = document.getElementById("fee_type").value;
    pageStyle = fee_type;
  }

  const title = pageInfo[pageStyle].title;
  const info = pageInfo[pageStyle].info;
  document.getElementById("page-title").innerHTML = title;
  document.getElementById("page-info").innerHTML = info;
};

if (document.getElementById("fee_type")) {
  document.getElementById("fee_type").addEventListener("change", updateInfo);
}
document.addEventListener("DOMContentLoaded", updateInfo);
