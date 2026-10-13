// Step 1: Wait for the page to fully load, then attach the form handler
document.addEventListener("DOMContentLoaded", function () {

    // Step 2: Get the form element by its ID
    const form = document.getElementById("registrationForm");
    const messageBox = document.getElementById("message");

    // Step 3: Listen for the form "submit" event
    form.addEventListener("submit", function (event) {

        // Step 4: Prevent the default form behavior
        // (By default, HTML forms reload the page when submitted.
        //  We don't want that — we want JavaScript to handle it.)
        event.preventDefault();

        // Step 5: Read the values from each form field
        const name = document.getElementById("name").value;
        const email = document.getElementById("email").value;
        const phone = document.getElementById("phone").value;
        const course = document.getElementById("course").value;

        // Read the selected radio button for gender
        const genderInput = document.querySelector('input[name="gender"]:checked');
        const gender = genderInput ? genderInput.value : "";

        // Step 6: Create a JavaScript object with the form data
        const formData = {
            name: name,
            email: email,
            phone: phone,
            course: course,
            gender: gender,
        };

        // Step 7: Send the data to Flask using fetch() API
        // fetch() sends an HTTP request from JavaScript to the server
        fetch("/api/register", {
            method: "POST",                              // HTTP method
            headers: {
                "Content-Type": "application/json",      // Tell Flask we are sending JSON
            },
            body: JSON.stringify(formData),               // Convert JS object to JSON string
        })
        .then(function (response) {
            // Step 8: Convert the response to JSON
            return response.json();
        })
        .then(function (data) {
            // Step 9: Show success or error message

            if (data.status === "success") {
                // Show success message (green)
                messageBox.textContent = data.message;
                messageBox.className = "message success";
                messageBox.style.display = "block";

                // Clear the form
                form.reset();
            } else {
                // Show error message (red)
                messageBox.textContent =  data.message;
                messageBox.className = "message error";
                messageBox.style.display = "block";
            }
        })
        .catch(function (error) {
            // Step 10: Handle network errors
            messageBox.textContent = " Network error. Please try again.";
            messageBox.className = "message error";
            messageBox.style.display = "block";
            console.error("Error:", error);
        });

    });  

});  