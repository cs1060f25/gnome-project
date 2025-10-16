import { useState } from 'react';

export default function Home() {
  const [messages, setMessages] = useState([{ text: 'Enter email:', from: 'bot' }]);
  const [input, setInput] = useState('');
  const [step, setStep] = useState(0); // 0: email, 1: password

  const handleSend = async () => {
    setMessages(prev => [...prev, { text: input, from: 'user' }]);
    if (step === 0) {
      setMessages(prev => [...prev, { text: 'Enter password:', from: 'bot' }]);
      setStep(1);
    } else {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: messages[1].text, password: input })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { text: data.message, from: 'bot' }]);
    }
    setInput('');
  };

  return (
    <div>
      <h1>Conversational Login</h1>
      {messages.map((msg, i) => <p key={i}>{msg.from}: {msg.text}</p>)}
      <input value={input} onChange={e => setInput(e.target.value)} />
      <button onClick={handleSend}>Send</button>
    </div>
  );
}