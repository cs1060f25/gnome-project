const express = require('express');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(express.json());
app.use(cors());

mongoose.connect('mongodb://localhost:27017/gnome', { useNewUrlParser: true, useUnifiedTopology: true });

const userSchema = new mongoose.Schema({ email: String, password: String });
const User = mongoose.model('User', userSchema);

app.post('/login', async (req, res) => {
  const { email, password } = req.body;
  const user = await User.findOne({ email });
  if (user && await bcrypt.compare(password, user.password)) {
    const token = jwt.sign({ email }, 'secret');
    res.json({ token });
  } else {
    res.status(401).json({ message: 'Invalid' });
  }
});

app.post('/register', async (req, res) => {
  const { email, password } = req.body;
  const hashed = await bcrypt.hash(password, 10);
  const user = new User({ email, password: hashed });
  await user.save();
  res.json({ message: 'Registered' });
});

app.use(express.static(path.join(__dirname, 'client/build')));
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'client/build/index.html')));

app.listen(3000, () => console.log('Server running'));