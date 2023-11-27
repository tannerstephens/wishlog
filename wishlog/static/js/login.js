window.onload = () => {
    const loginForm = document.forms['login'];

    loginForm.onsubmit = e => {
        e.preventDefault();

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
                }
            });
    }
}
