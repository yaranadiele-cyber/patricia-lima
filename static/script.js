const track = document.querySelector('.carousel-track');
const dotsContainer = document.querySelector('.dots');

// Função principal para rodar o carrossel
function initCarousel() {
    let images = document.querySelectorAll('.carousel-track img');
    if (images.length === 0) return;

    let index = 0;
    const totalImagensNoHtml = images.length;
    const realTotal = totalImagensNoHtml / 2; 

    /* Criar bolinhas dinamicamente */
    dotsContainer.innerHTML = ''; 
    for (let i = 0; i < realTotal; i++) {
        const dot = document.createElement('span');
        if (i === 0) dot.classList.add('active');
        dotsContainer.appendChild(dot);
    }

    let dots = document.querySelectorAll('.dots span');

    function updateCarousel(animate = true) {
        const width = images[0].clientWidth + 12; // Largura + Gap

        if (!animate) track.style.transition = "none";
        else track.style.transition = "transform 0.6s ease";

        track.style.transform = `translateX(${-index * width}px)`;

        /* Atualizar Bolinhas */
        dots.forEach(dot => dot.classList.remove('active'));
        if (dots[index % realTotal]) {
            dots[index % realTotal].classList.add('active');
        }
    }

    function nextSlide() {
        if (realTotal <= 1) return;
        index++;
        updateCarousel(true);

        if (index >= realTotal) {
            setTimeout(() => {
                index = 0;
                updateCarousel(false);
            }, 600);
        }
    }

    // Giro automático
    let autoScroll = setInterval(nextSlide, 2800);

    /* SWIPE MOBILE */
    let startX = 0;
    track.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
        clearInterval(autoScroll);
    });

    track.addEventListener('touchend', e => {
        let endX = e.changedTouches[0].clientX;
        let diff = startX - endX;

        if (diff > 50) nextSlide();
        else if (diff < -50) {
            index--;
            if (index < 0) index = realTotal - 1;
            updateCarousel();
        }
        autoScroll = setInterval(nextSlide, 2800);
    });

    window.addEventListener('resize', () => updateCarousel(false));
    updateCarousel();
}

// EXECUÇÃO: Garante que o código rode mesmo que a imagem demore a carregar
window.addEventListener('load', initCarousel);