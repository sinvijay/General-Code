import {BrowserRouter, Routes, Route, Link} from "react-router-dom"
import Home from "./components/Home"
import About from "./components/about"
import Contacts from "./components/Contacts"


function Navbar () {
  

  
  return (
    <BrowserRouter>
      
      <h1> SynergyApp </h1>

      <Link to={"/"}>Home</Link>
      <Link to={"/About"}>About</Link>
      <Link to={"/Contacts"}>Contacts</Link>
      

      <Routes>
        <Route path="/" element={<Home/>}/>
        <Route path="/about" element={<About/>}/>
        <Route path="/Contacts" element={<Contacts/>}/>
        
        
      </Routes>
    </BrowserRouter>
  )
}

export default Navbar