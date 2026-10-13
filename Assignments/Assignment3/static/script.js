
document.addEventListener("DOMContentLoaded", function () {

    // Step 1: Get the form and message elements
    const form = document.getElementById("registrationForm");
    const messageBox = document.getElementById("message");

    // Get validation message elements
    const skillsError = document.getElementById("skillsError");
    const passwordError = document.getElementById("passwordError");

    // Step 2: Listen for form submission
    form.addEventListener("submit", async function (event) {

        // Prevent default form submission
        event.preventDefault();

        // Clear previous messages
        messageBox.textContent = "";
        messageBox.style.display = "none";

        skillsError.textContent = "";
        passwordError.textContent = "";

        // Step 3: Read form values
        const name = document.getElementById("name").value.trim();
        const email = document.getElementById("email").value.trim();
        const phone = document.getElementById("phone").value.trim();
        const dob = document.getElementById("dob").value;
        const course = document.getElementById("course").value;

        const qualification =
            document.getElementById("qualification").value;

        const experience =
            document.getElementById("experience").value;

        const address =
            document.getElementById("address").value.trim();

        const website =
            document.getElementById("website").value.trim();

        // Step 4: Get selected gender
        const genderInput = document.querySelector(
            'input[name="gender"]:checked'
        );

        const gender = genderInput ? genderInput.value : "";

        // Step 5: Get selected training mode
        const trainingModeInput = document.querySelector(
            'input[name="training_mode"]:checked'
        );

        const trainingMode = trainingModeInput
            ? trainingModeInput.value
            : "";

        // Step 6: Get selected skills
        const skillInputs = document.querySelectorAll(
            'input[name="skills"]:checked'
        );

        const skills = Array.from(skillInputs).map(function (input) {
            return input.value;
        });

        // Step 7: Read password fields
        const password = document.getElementById("password").value;

        const confirmPassword =
            document.getElementById("confirm_password").value;

        // Step 8: Validate skills
        if (skills.length === 0) {
            skillsError.textContent =
                "Please select at least one skill.";
            return;
        }

        // Step 9: Validate password confirmation
        if (password !== confirmPassword) {
            passwordError.textContent =
                "Password and confirm password do not match.";
            return;
        }

        // Step 10: Check agreement
        const agree = document.getElementById("agree").checked;

        if (!agree) {
            messageBox.textContent =
                "Please agree to register before submitting.";
            messageBox.className = "message error";
            messageBox.style.display = "block";
            return;
        }

        // Step 11: Create an object with all registration data
        const formData = {
            name: name,
            email: email,
            phone: phone,
            dob: dob,
            gender: gender,
            course: course,
            qualification: qualification,
            training_mode: trainingMode,
            skills: skills,
            experience: experience,
            address: address,
            website: website,
            password: password,
            confirm_password: confirmPassword,
            agree: agree
        };

        // Step 12: Show loading message
        messageBox.textContent = "Registering student...";
        messageBox.className = "message";
        messageBox.style.display = "block";

        const submitButton = form.querySelector(
            'button[type="submit"]'
        );

        submitButton.disabled = true;

        try {

            // Step 13: Send JSON data to Flask API
            const response = await fetch("/api/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(formData)
            });

            // Step 14: Read server response
            const data = await response.json();

            // Step 15: Display result
            if (response.ok && data.status === "success") {

                messageBox.textContent =
                    data.message || "Registration successful!";

                messageBox.className = "message success";

                // Reset form after successful registration
                form.reset();

            } else {

                messageBox.textContent =
                    data.message || "Registration failed. Please try again.";

                messageBox.className = "message error";
            }

        } catch (error) {

            // Step 16: Handle network errors
            messageBox.textContent =
                "Network error. Please try again.";

            messageBox.className = "message error";

            console.error("Registration error:", error);

        } finally {

            // Step 17: Enable submit button again
            submitButton.disabled = false;
        }

    });

});
