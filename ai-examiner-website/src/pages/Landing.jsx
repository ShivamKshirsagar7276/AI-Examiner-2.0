import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen text-brandTextSoft overflow-hidden">

      {/* 🔥 HERO SECTION */}
      <section className="relative flex flex-col items-center justify-center text-center h-screen px-6">

        {/* Animated Background Glow */}
        <div className="absolute w-[600px] h-[600px] bg-brandCard opacity-10 rounded-full blur-3xl top-[-200px] left-[-200px]"></div>
        <div className="absolute w-[500px] h-[500px] bg-brandCard opacity-10 rounded-full blur-3xl bottom-[-150px] right-[-150px]"></div>

        <motion.h1
          initial={{ opacity: 0, y: -40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-6xl font-bold mb-6"
        >
          AI Examiner
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-lg text-brandMuted max-w-xl"
        >
          Intelligent AI-based examination system with automated evaluation,
          instant results, and professional digital marksheet generation.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex gap-6 mt-10"
        >
          <button
            onClick={() => navigate("/result")}
            className="bg-brandCard text-brandDark px-8 py-3 rounded-xl font-semibold shadow-xl hover:scale-105 transition duration-300"
          >
            Check Result
          </button>

          <button
            onClick={() => navigate("/faculty/login")}
            className="border border-brandCard px-8 py-3 rounded-xl hover:bg-brandCard hover:text-brandDark transition duration-300"
          >
            Faculty Login
          </button>
        </motion.div>
      </section>

      {/* 🚀 FEATURES SECTION */}
      <section className="py-24 px-8">
        <h2 className="text-3xl font-bold text-center mb-16">
          Powerful Features
        </h2>

        <div className="grid md:grid-cols-3 gap-10 max-w-6xl mx-auto">

          {[
            "AI Based Evaluation",
            "Automatic Marks Calculation",
            "Instant Result Publishing",
            "Secure Role Management",
            "Digital Marksheet Download",
            "Multi Subject Support"
          ].map((feature, index) => (
            <motion.div
              key={index}
              whileHover={{ scale: 1.05 }}
              className="bg-brandCard/20 backdrop-blur-md border border-brandCard/30 rounded-2xl p-8 shadow-lg"
            >
              <h3 className="text-xl font-semibold mb-3">{feature}</h3>
              <p className="text-brandMuted text-sm">
                Advanced system built for educational institutions with
                reliability and precision.
              </p>
            </motion.div>
          ))}

        </div>
      </section>

      {/* 🧠 HOW IT WORKS */}
      <section className="py-24 px-8 bg-brandDark/30">
        <h2 className="text-3xl font-bold text-center mb-16">
          How It Works
        </h2>

        <div className="max-w-4xl mx-auto space-y-10">

          {[
            "Faculty uploads exam papers",
            "AI evaluates answer sheets",
            "Faculty publishes results",
            "Students check & download marksheet"
          ].map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="bg-brandCard/20 border border-brandCard/30 rounded-xl p-6"
            >
              <h4 className="text-lg font-semibold">
                Step {index + 1}
              </h4>
              <p className="text-brandMuted mt-2">{step}</p>
            </motion.div>
          ))}

        </div>
      </section>

      {/* 💎 FOOTER CTA */}
      <section className="py-16 text-center">
        <h2 className="text-2xl font-bold mb-4">
          Ready to Experience Smart Evaluation?
        </h2>

        <button
          onClick={() => navigate("/result")}
          className="bg-brandCard text-brandDark px-8 py-3 rounded-xl font-semibold shadow-lg hover:scale-105 transition duration-300"
        >
          View Results Now
        </button>
      </section>

    </div>
  );
}