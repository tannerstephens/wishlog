window.onload = () => {
    const registrationForm = document.forms['register'];
    const formError = document.getElementById('formError');
    const submitButton = registrationForm.querySelector('button[type="submit"]');

    const showError = message => {
        formError.textContent = message;
        formError.classList.remove('is-hidden');
    };

    registrationForm.onsubmit = e => {
        e.preventDefault();

        formError.classList.add('is-hidden');
        submitButton.disabled = true;

        fetch('/api/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: registrationForm['username'].value,
                password: registrationForm['password'].value
            })
        })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    window.location = '/login';
                } else {
                    showError(data.message || 'Registration failed');
                }
            })
            .catch(() => showError('Could not reach the server, please try again'))
            .finally(() => { submitButton.disabled = false; });
    }
}
