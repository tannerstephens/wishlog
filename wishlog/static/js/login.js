window.onload = () => {
    const loginForm = document.forms['login'];
    const formError = document.getElementById('formError');
    const submitButton = loginForm.querySelector('button[type="submit"]');

    const showError = message => {
        formError.textContent = message;
        formError.classList.remove('is-hidden');
    };

    loginForm.onsubmit = e => {
        e.preventDefault();

        formError.classList.add('is-hidden');
        submitButton.disabled = true;
        submitButton.classList.add('is-loading');

        fetch('/api/session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: loginForm['username'].value,
                password: loginForm['password'].value
            })
        })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    window.location = '/';
                } else {
                    showError(data.message || 'Login failed');
                }
            })
            .catch(() => showError('Could not reach the server, please try again'))
            .finally(() => {
                submitButton.disabled = false;
                submitButton.classList.remove('is-loading');
            });
    }
}
