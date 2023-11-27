window.onload = () => {
    const registrationForm = document.forms['register'];

    registrationForm.onsubmit = e => {
        e.preventDefault();

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
                }
            });
    }
}
