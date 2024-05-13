function fetchLogs() {
    fetch('/logs')
        .then(response => response.json())
        .then(data => {
            const logOutput = document.getElementById('log-output');
            logOutput.innerHTML = data.join('\n');
        });
}

function toggleCheckbox(checkbox) {
  var label = checkbox.nextElementSibling;
  if (checkbox.checked) {
    label.innerHTML = "已选中";
  } else {
    label.innerHTML = "";
  }
}

function togglePassword() {
    var passwordInput = document.getElementById("passwordInput");
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
    } else {
        passwordInput.type = "password";
    }
}

//function fetchTask() {
//    fetch('/task')
//        .then(response => response.json())
//        .then(data => {
//            const logOutput = document.getElementById('get_task_title');
//            logOutput.innerHTML = data.join('\n');
//        });
//}

// Clear form data when the page is refreshed
window.onload = function() {
    document.getElementById("my-form").reset();
}
//setInterval(fetchTask, 1000);
setInterval(fetchLogs, 1500);
