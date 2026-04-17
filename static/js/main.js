/* MENU HAMBURGER */
function toggleMenu() {
    const menu = document.getElementById("menu");
    menu.classList.toggle("active");
}

// Fechar menu ao clicar em um link
document.querySelectorAll(".menu-mobile a").forEach(link => {
    link.addEventListener("click", () => {
        document.getElementById("menu").classList.remove("active");
    });
});

// Fechar menu ao clicar fora
document.addEventListener("click", (e) => {
    const header = document.querySelector(".header");
    const menu = document.getElementById("menu");
    if (!header.contains(e.target) && menu.classList.contains("active")) {
        menu.classList.remove("active");
    }
});

/* FADE IN ANIMATIONS AO SCROLL */
function observeFadeElements() {
    const elements = document.querySelectorAll(".fade-in");
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    elements.forEach(el => observer.observe(el));
}

// Iniciar observer quando DOM está pronto
document.addEventListener("DOMContentLoaded", observeFadeElements);

const modal = document.getElementById("pixModal");
const abrirModalBtns = document.querySelectorAll(".abrir-modal");
const fecharModal = document.getElementById("fecharModal");
const btnFecharModal = document.getElementById("btnFecharModal");

const modalTitulo = document.getElementById("modalTitulo");
const modalValor = document.getElementById("modalValor");
const modalChave = document.getElementById("modalChave");
const modalTipo = document.getElementById("modalTipo");
const pixCopiaCola = document.getElementById("pixCopiaCola");
const btnCopiarPix = document.getElementById("btnCopiarPix");
const copyFeedback = document.getElementById("copyFeedback");

function abrirModalPresente(botao) {
    modalTitulo.textContent = botao.dataset.titulo;
    modalValor.textContent = botao.dataset.valor;
    modalChave.textContent = botao.dataset.chave;
    modalTipo.textContent = botao.dataset.tipo;
    pixCopiaCola.value = botao.dataset.copia;

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function fecharModalPresente() {
    modal.classList.add("hidden");
    document.body.style.overflow = "auto";
    copyFeedback.classList.add("hidden");
}

abrirModalBtns.forEach((botao) => {
    botao.addEventListener("click", () => abrirModalPresente(botao));
});

fecharModal?.addEventListener("click", fecharModalPresente);
btnFecharModal?.addEventListener("click", fecharModalPresente);

btnCopiarPix?.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(pixCopiaCola.value);
        copyFeedback.classList.remove("hidden");
        soltarConfetes();
    } catch (error) {
        alert("Não foi possível copiar o código PIX.");
    }
});

function soltarConfetes() {
    for (let i = 0; i < 18; i++) {
        const confete = document.createElement("span");
        confete.className = "confete";
        confete.style.left = `${50 + (Math.random() * 120 - 60)}%`;
        confete.style.top = "45%";
        confete.style.position = "fixed";
        confete.style.width = "8px";
        confete.style.height = "14px";
        confete.style.background = i % 2 === 0 ? "#A7C7E7" : "#DCEAF7";
        confete.style.borderRadius = "3px";
        confete.style.zIndex = "1000";
        confete.style.pointerEvents = "none";
        confete.style.transition = "transform 1s ease, opacity 1s ease";
        document.body.appendChild(confete);

        requestAnimationFrame(() => {
            confete.style.transform = `translate(${Math.random() * 220 - 110}px, ${Math.random() * 220 + 100}px) rotate(${Math.random() * 360}deg)`;
            confete.style.opacity = "0";
        });

        setTimeout(() => confete.remove(), 1000);
    }
}

function iniciarContagemRegressiva() {
    const dataCasamento = new Date("2026-10-10T15:30:00");

    const diasEl = document.getElementById("dias");
    const horasEl = document.getElementById("horas");
    const minutosEl = document.getElementById("minutos");
    const segundosEl = document.getElementById("segundos");

    function atualizarContador() {
        const agora = new Date();
        const diferenca = dataCasamento - agora;

        if (diferenca <= 0) {
            diasEl.textContent = "0";
            horasEl.textContent = "0";
            minutosEl.textContent = "0";
            if (segundosEl) segundosEl.textContent = "0";
            return;
        }

        const dias = Math.floor(diferenca / (1000 * 60 * 60 * 24));
        const horas = Math.floor((diferenca / (1000 * 60 * 60)) % 24);
        const minutos = Math.floor((diferenca / (1000 * 60)) % 60);
        const segundos = Math.floor((diferenca / 1000) % 60);

        diasEl.textContent = dias;
        horasEl.textContent = horas;
        minutosEl.textContent = minutos;
        if (segundosEl) segundosEl.textContent = segundos;
    }

    atualizarContador();
    setInterval(atualizarContador, 1000);
}

iniciarContagemRegressiva();