import React from 'react';
import './App.css';
import FlagList from './components/Flags';

const App = () => {
  return (
    <div className="App">
      <header className="App-header">
        <h1>What's that flag?</h1>
      </header>
      <main>
        <FlagList />
      </main>
    </div>
  );
};

export default App;
